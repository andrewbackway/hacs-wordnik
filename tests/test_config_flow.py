"""Tests for the Wordnik config flow."""

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.wordnik.api import WordnikAuthError
from custom_components.wordnik.const import (
    CONF_API_KEY,
    CONF_ROLLOVER,
    CONF_TIER,
    CONF_TIERS,
    DOMAIN,
)


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    """A valid submission creates an entry for the chosen tier."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    with (
        patch(
            "custom_components.wordnik.config_flow.WordnikApiClient.async_validate_key",
            new=AsyncMock(),
        ),
        patch("custom_components.wordnik.async_setup_entry", return_value=True),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_API_KEY: "key",
                CONF_TIERS: ["everyday"],
                CONF_ROLLOVER: "00:00:00",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_TIER] == "everyday"
    assert result2["options"][CONF_ROLLOVER] == "00:00:00"


async def test_user_flow_invalid_auth(hass: HomeAssistant) -> None:
    """A rejected key shows an error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.wordnik.config_flow.WordnikApiClient.async_validate_key",
        side_effect=WordnikAuthError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_API_KEY: "bad",
                CONF_TIERS: ["everyday"],
                CONF_ROLLOVER: "00:00:00",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}
