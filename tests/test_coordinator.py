"""Tests for the Wordnik coordinator."""

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wordnik.const import (
    CONF_API_KEY,
    CONF_ROLLOVER,
    CONF_TIER,
    DOMAIN,
)
from custom_components.wordnik.coordinator import WordnikDataUpdateCoordinator


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "key", CONF_TIER: "everyday"},
        options={CONF_ROLLOVER: "00:00:00"},
    )


def _api(audio: bool = True) -> AsyncMock:
    api = AsyncMock()
    api.async_random_words.return_value = ["serendipity"]
    api.async_definitions.return_value = [
        {"text": "a happy accident", "partOfSpeech": "noun", "attributionText": "src"}
    ]
    api.async_audio.return_value = (
        [{"fileUrl": "https://a/serendipity.mp3", "duration": 1}] if audio else []
    )
    api.async_examples.return_value = [{"text": "what serendipity"}]
    api.async_pronunciations.return_value = [{"raw": "ser", "rawType": "IPA"}]
    api.async_download.return_value = b"ID3-audio-bytes"
    return api


async def test_assemble_enriches_first_word_with_definition(hass: HomeAssistant) -> None:
    """The first usable definition wins, even when a later word has audio."""
    entry = _entry()
    entry.add_to_hass(hass)
    store = AsyncMock()
    store.async_load.return_value = None
    api = _api()
    api.async_random_words.return_value = ["first", "second"]
    api.async_audio.return_value = [{"fileUrl": "https://a/first.mp3", "duration": 1}]
    api.async_definitions.side_effect = [
        [{"text": "first definition", "partOfSpeech": "noun"}],
        [{"text": "second definition", "partOfSpeech": "noun"}],
    ]

    coordinator = WordnikDataUpdateCoordinator(
        hass, entry, api, store, "everyday"
    )
    data = await coordinator._async_update_data()

    assert data["word"] == "first"
    assert data["definition"] == "first definition"
    assert data["example"] == "what serendipity"
    assert data["audio_source_url"] == "https://a/first.mp3"
    assert data["audio_url"].startswith(f"/{DOMAIN}/audio/")
    assert data["audio_url"].endswith("first.mp3")
    assert data["pronunciation"] == "ser"
    assert data["tier_name"] == "Everyday"
    api.async_definitions.assert_awaited_once()
    api.async_audio.assert_awaited_once_with("first")
    api.async_examples.assert_awaited_once_with("first", 5)
    api.async_pronunciations.assert_awaited_once_with("first")
    store.async_save.assert_awaited_once()


async def test_assemble_removes_definition_xref_markup(hass: HomeAssistant) -> None:
    """Wordnik cross-reference tags are presentation markup, not definition text."""
    entry = _entry()
    entry.add_to_hass(hass)
    store = AsyncMock()
    store.async_load.return_value = None
    api = _api()
    api.async_definitions.return_value = [
        {
            "text": "A <xref>radioactive</xref> <xref>isotope</xref>.",
            "partOfSpeech": "noun",
        },
        {"text": "A second definition with <xref>links</xref>.", "partOfSpeech": "noun"},
    ]

    coordinator = WordnikDataUpdateCoordinator(hass, entry, api, store, "everyday")
    data = await coordinator._async_update_data()

    assert data["definition"] == "A radioactive isotope."
    assert data["definitions"] == [
        "A radioactive isotope.",
        "A second definition with links.",
    ]


async def test_stored_definition_xref_markup_is_cleaned(hass: HomeAssistant) -> None:
    """Persisted definitions are cleaned when loaded after an upgrade."""
    entry = _entry()
    entry.add_to_hass(hass)
    store = AsyncMock()
    api = _api()
    coordinator = WordnikDataUpdateCoordinator(hass, entry, api, store, "everyday")
    store.async_load.return_value = {
        "date": coordinator._logical_date(),
        "data": {
            "word": "serendipity",
            "definition": "A <xref type=\"word\">happy</xref> accident.",
            "definitions": ["A <XREF>fortunate</XREF> discovery."],
        },
    }

    await coordinator.async_load_stored()
    data = await coordinator._async_update_data()

    assert data["definition"] == "A happy accident."
    assert data["definitions"] == ["A fortunate discovery."]
    api.async_definitions.assert_not_awaited()


async def test_audio_cached_locally_and_old_files_removed(hass: HomeAssistant) -> None:
    """A newly picked word's audio is written to disk and stale clips pruned."""
    import os

    from custom_components.wordnik.const import AUDIO_CACHE_DIRNAME

    entry = _entry()
    entry.add_to_hass(hass)
    store = AsyncMock()
    store.async_load.return_value = None

    cache_dir = hass.config.path(AUDIO_CACHE_DIRNAME)
    os.makedirs(cache_dir, exist_ok=True)
    stale = os.path.join(cache_dir, f"{entry.entry_id}_oldword.mp3")
    with open(stale, "wb") as handle:
        handle.write(b"old")

    coordinator = WordnikDataUpdateCoordinator(hass, entry, _api(), store, "everyday")
    data = await coordinator._async_update_data()

    filename = data["audio_url"].rsplit("/", 1)[-1]
    assert os.path.exists(os.path.join(cache_dir, filename))
    assert not os.path.exists(stale)



async def test_stored_word_reused_same_day(hass: HomeAssistant) -> None:
    """When today's word is stored, no API call is made."""
    entry = _entry()
    entry.add_to_hass(hass)
    api = _api()
    store = AsyncMock()

    coordinator = WordnikDataUpdateCoordinator(hass, entry, api, store, "everyday")
    logical = coordinator._logical_date()
    coordinator._stored = {"date": logical, "data": {"word": "cached"}}

    data = await coordinator._async_update_data()

    assert data["word"] == "cached"
    api.async_random_words.assert_not_called()


async def test_new_word_bypasses_cache(hass: HomeAssistant) -> None:
    """Requesting a new word ignores the cached word."""
    entry = _entry()
    entry.add_to_hass(hass)
    api = _api()
    store = AsyncMock()

    coordinator = WordnikDataUpdateCoordinator(hass, entry, api, store, "everyday")
    logical = coordinator._logical_date()
    coordinator._stored = {"date": logical, "data": {"word": "cached"}}
    coordinator._force_new = True

    data = await coordinator._async_update_data()

    assert data["word"] == "serendipity"
    api.async_random_words.assert_called_once()


async def test_assemble_retries_without_corpus_filters(hass: HomeAssistant) -> None:
    """An empty corpus-filtered result is retried with length filters intact."""
    entry = _entry()
    entry.add_to_hass(hass)
    api = _api()
    api.async_random_words.side_effect = [[], ["serendipity"]]
    store = AsyncMock()
    store.async_load.return_value = None

    coordinator = WordnikDataUpdateCoordinator(
        hass, entry, api, store, "everyday"
    )
    data = await coordinator._async_update_data()

    assert data["word"] == "serendipity"
    assert api.async_random_words.await_count == 2
    first_profile, second_profile = (
        call.args[0] for call in api.async_random_words.await_args_list
    )
    assert first_profile["min_corpus"] == 50000
    assert "min_corpus" not in second_profile
