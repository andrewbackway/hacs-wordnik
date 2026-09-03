"""Data update coordinator for the Wordnik integration."""

from __future__ import annotations

import logging
import os
import re
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import WordnikApiClient, WordnikError
from .const import (
    AUDIO_CACHE_DIRNAME,
    AUDIO_URL_BASE,
    CANDIDATE_LIMIT,
    CONF_BLOCKLIST,
    CONF_ROLLOVER,
    DEFAULT_ROLLOVER,
    DEFINITIONS_LIMIT,
    DOMAIN,
    EXAMPLES_LIMIT,
    MAX_ASSEMBLE_ATTEMPTS,
    TIERS,
    WORD_URL,
)

_LOGGER = logging.getLogger(__name__)


class WordnikDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    """Coordinate the daily Wordnik word fetch for a single tier."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: WordnikApiClient,
        store: Store,
        tier: str,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(hass, _LOGGER, name=f"{DOMAIN}_{tier}", config_entry=entry)
        self.entry = entry
        self.api = api
        self.store = store
        self.tier = tier
        self._force_new = False
        self._stored: dict | None = None

    async def async_load_stored(self) -> None:
        """Load the persisted word so restarts don't re-pick within a day."""
        self._stored = await self.store.async_load()

    async def async_request_new_word(self) -> None:
        """Force a fresh word pick, bypassing the daily seed."""
        self._force_new = True
        await self.async_request_refresh()

    def _rollover(self) -> tuple[int, int, int]:
        """Return the configured rollover time as (hour, minute, second)."""
        raw = self.entry.options.get(CONF_ROLLOVER, DEFAULT_ROLLOVER)
        parts = [int(p) for p in raw.split(":")]
        while len(parts) < 3:
            parts.append(0)
        return parts[0], parts[1], parts[2]

    def _logical_date(self) -> str:
        """Return the date key for the current word, honouring the rollover."""
        hour, minute, second = self._rollover()
        now = dt_util.now()
        boundary = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
        current = now.date()
        if now < boundary:
            current = current - timedelta(days=1)
        return current.isoformat()

    async def _async_update_data(self) -> dict:
        """Return the word for the current day, fetching a new one if needed."""
        logical = self._logical_date()
        if (
            not self._force_new
            and self._stored is not None
            and self._stored.get("date") == logical
        ):
            return self._stored["data"]

        try:
            data = await self._assemble(logical)
        except WordnikError as err:
            if self._stored is not None:
                _LOGGER.warning("Wordnik fetch failed, keeping last word: %s", err)
                return self._stored["data"]
            raise UpdateFailed(str(err)) from err

        await self._cache_audio(data)

        self._force_new = False
        self._stored = {"date": logical, "data": data}
        await self.store.async_save(self._stored)
        return data

    async def _cache_audio(self, data: dict) -> None:
        """Download the word's audio locally and point the sensor at the copy.

        Wordnik audio fileUrls are signed and expire, so we fetch the clip on
        each word update, serve it ourselves, and drop this tier's previous
        cached clip to avoid piling up stale files. Any failure here is
        non-fatal: we keep the original remote URL so the update still succeeds.
        """
        remote_url = data.get("audio_url")
        if not remote_url:
            return

        try:
            safe_word = re.sub(
                r"[^a-z0-9]+", "-", (data.get("word") or "").lower()
            ).strip("-")
            filename = f"{self.entry.entry_id}_{safe_word}.mp3"
            cache_dir = self.hass.config.path(AUDIO_CACHE_DIRNAME)
            dest = os.path.join(cache_dir, filename)

            audio = await self.api.async_download(remote_url)

            def _write() -> None:
                os.makedirs(cache_dir, exist_ok=True)
                prefix = f"{self.entry.entry_id}_"
                for existing in os.listdir(cache_dir):
                    if existing.startswith(prefix) and existing != filename:
                        try:
                            os.remove(os.path.join(cache_dir, existing))
                        except OSError:
                            pass
                with open(dest, "wb") as handle:
                    handle.write(audio)

            await self.hass.async_add_executor_job(_write)
        except Exception as err:  # noqa: BLE001 - caching must never break updates
            _LOGGER.warning(
                "Could not cache audio for %s: %s", data.get("word"), err
            )
            return

        data["audio_source_url"] = remote_url
        data["audio_url"] = f"{AUDIO_URL_BASE}/{filename}"

    async def _assemble(self, logical_date: str) -> dict:
        """Pick a tier-appropriate word and gather its details."""
        profile = TIERS[self.tier]
        blocklist = {
            w.strip().lower()
            for w in self.entry.options.get(CONF_BLOCKLIST, "").split(",")
            if w.strip()
        }
        candidates = await self.api.async_random_words(profile, CANDIDATE_LIMIT)
        if not candidates and (profile.get("min_corpus") or profile.get("max_corpus")):
            relaxed_profile = {
                key: value
                for key, value in profile.items()
                if key not in ("min_corpus", "max_corpus")
            }
            _LOGGER.debug(
                "No candidates returned for %s with corpus filters; retrying without them",
                self.tier,
            )
            candidates = await self.api.async_random_words(
                relaxed_profile, CANDIDATE_LIMIT
            )
        _LOGGER.debug("Wordnik returned %d candidates for tier %s", len(candidates), self.tier)

        attempts = 0
        for word in candidates:
            if word.lower() in blocklist:
                continue
            attempts += 1
            if attempts > MAX_ASSEMBLE_ATTEMPTS:
                break

            definitions = await self.api.async_definitions(word, DEFINITIONS_LIMIT)
            primary = next((d for d in definitions if d.get("text")), None)
            if primary is None:
                continue

            audio = await self.api.async_audio(word)
            examples = await self.api.async_examples(word, EXAMPLES_LIMIT)
            pronunciations = await self.api.async_pronunciations(word)
            return self._build(
                word, logical_date, primary, definitions, examples, audio, pronunciations
            )

        raise WordnikError("No suitable word found for tier")

    def _build(
        self,
        word: str,
        logical_date: str,
        primary: dict,
        definitions: list[dict],
        examples: list[dict],
        audio: list[dict],
        pronunciations: list[dict],
    ) -> dict:
        """Assemble the payload consumed by the sensors and card."""
        audio_clip = next((a for a in audio if a.get("fileUrl")), None)
        example = next((e for e in examples if e.get("text")), None)
        pron = next((p for p in pronunciations if p.get("raw")), None)

        return {
            "word": word,
            "part_of_speech": primary.get("partOfSpeech"),
            "definition": primary.get("text"),
            "definitions": [d["text"] for d in definitions if d.get("text")],
            "source_dictionary": primary.get("sourceDictionary"),
            "example": example.get("text") if example else None,
            "examples": [e["text"] for e in examples if e.get("text")],
            "audio_url": audio_clip.get("fileUrl") if audio_clip else None,
            "audio_duration": audio_clip.get("duration") if audio_clip else None,
            "audio": [
                {"url": a.get("fileUrl"), "duration": a.get("duration")}
                for a in audio
                if a.get("fileUrl")
            ],
            "pronunciation": pron.get("raw") if pron else None,
            "pronunciation_type": pron.get("rawType") if pron else None,
            "pronunciations": [p["raw"] for p in pronunciations if p.get("raw")],
            "attribution": primary.get("attributionText"),
            "tier": self.tier,
            "tier_name": TIERS[self.tier]["name"],
            "date": logical_date,
            "word_url": WORD_URL.format(word=word),
        }
