"""Tests for the Wordnik button platform."""

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wordnik.button import WordnikNewWordButton
from custom_components.wordnik.const import CONF_API_KEY, CONF_TIER, DOMAIN


async def test_new_word_button_requests_new_word(hass: HomeAssistant) -> None:
    """Pressing the button bypasses the daily word cache."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "key", CONF_TIER: "everyday"},
    )
    coordinator = AsyncMock()
    button = WordnikNewWordButton(coordinator, entry)

    await button.async_press()

    coordinator.async_request_new_word.assert_awaited_once_with()