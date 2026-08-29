"""Config and options flow for the Wordnik integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WordnikApiClient, WordnikAuthError, WordnikError
from .const import (
    AUDIO_MODE_BROWSER,
    AUDIO_MODE_MEDIA_PLAYER,
    CONF_API_KEY,
    CONF_AUDIO_MODE,
    CONF_BLOCKLIST,
    CONF_MEDIA_PLAYER,
    CONF_ROLLOVER,
    CONF_SHOW_PRONUNCIATION,
    CONF_TIER,
    CONF_TIERS,
    DEFAULT_AUDIO_MODE,
    DEFAULT_ROLLOVER,
    DEFAULT_SHOW_PRONUNCIATION,
    DOMAIN,
    TIER_EVERYDAY,
    TIERS,
)

_TIER_OPTIONS = [
    selector.SelectOptionDict(value=slug, label=meta["name"])
    for slug, meta in TIERS.items()
]
_AUDIO_OPTIONS = [
    selector.SelectOptionDict(value=AUDIO_MODE_BROWSER, label="In browser"),
    selector.SelectOptionDict(value=AUDIO_MODE_MEDIA_PLAYER, label="Media player"),
]


class WordnikConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Wordnik config flow."""

    VERSION = 1

    def _existing_api_key(self) -> str:
        """Return an API key from an existing entry, if any."""
        for entry in self._async_current_entries():
            if key := entry.data.get(CONF_API_KEY):
                return key
        return ""

    def _configured_tiers(self) -> set[str]:
        """Return tiers that already have an entry."""
        return {
            entry.data[CONF_TIER]
            for entry in self._async_current_entries()
            if CONF_TIER in entry.data
        }

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            api = WordnikApiClient(async_get_clientsession(self.hass), api_key)
            try:
                await api.async_validate_key()
            except WordnikAuthError:
                errors["base"] = "invalid_auth"
            except WordnikError:
                errors["base"] = "cannot_connect"
            else:
                configured = self._configured_tiers()
                tiers = [t for t in user_input[CONF_TIERS] if t not in configured]
                if not tiers:
                    errors["base"] = "already_configured"
                else:
                    rollover = user_input[CONF_ROLLOVER]
                    for extra in tiers[1:]:
                        self.hass.async_create_task(
                            self.hass.config_entries.flow.async_init(
                                DOMAIN,
                                context={"source": "import"},
                                data={
                                    CONF_API_KEY: api_key,
                                    CONF_TIER: extra,
                                    CONF_ROLLOVER: rollover,
                                },
                            )
                        )
                    return await self._create_entry(api_key, tiers[0], rollover)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_API_KEY, default=self._existing_api_key()
                ): selector.TextSelector(),
                vol.Required(
                    CONF_TIERS, default=[TIER_EVERYDAY]
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_TIER_OPTIONS,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_ROLLOVER, default=DEFAULT_ROLLOVER
                ): selector.TimeSelector(),
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_import(
        self, data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Create an entry for an additional tier selected during setup."""
        return await self._create_entry(
            data[CONF_API_KEY], data[CONF_TIER], data[CONF_ROLLOVER]
        )

    async def _create_entry(
        self, api_key: str, tier: str, rollover: str
    ) -> ConfigFlowResult:
        """Create a config entry for a single tier."""
        await self.async_set_unique_id(f"{DOMAIN}_{tier}")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=f"Wordnik – {TIERS[tier]['name']}",
            data={CONF_API_KEY: api_key, CONF_TIER: tier},
            options={CONF_ROLLOVER: rollover},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return WordnikOptionsFlow()


class WordnikOptionsFlow(OptionsFlow):
    """Handle Wordnik options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ROLLOVER,
                    default=options.get(CONF_ROLLOVER, DEFAULT_ROLLOVER),
                ): selector.TimeSelector(),
                vol.Required(
                    CONF_SHOW_PRONUNCIATION,
                    default=options.get(
                        CONF_SHOW_PRONUNCIATION, DEFAULT_SHOW_PRONUNCIATION
                    ),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_AUDIO_MODE,
                    default=options.get(CONF_AUDIO_MODE, DEFAULT_AUDIO_MODE),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_AUDIO_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_MEDIA_PLAYER,
                    description={
                        "suggested_value": options.get(CONF_MEDIA_PLAYER)
                    },
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="media_player")
                ),
                vol.Optional(
                    CONF_BLOCKLIST,
                    default=options.get(CONF_BLOCKLIST, ""),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
