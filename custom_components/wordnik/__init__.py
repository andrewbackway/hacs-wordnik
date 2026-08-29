"""The Wordnik Word of the Day integration."""

from __future__ import annotations

import logging
import os

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store

from .api import WordnikApiClient
from .const import (
    AUDIO_CACHE_DIRNAME,
    AUDIO_URL_BASE,
    CONF_API_KEY,
    CONF_TIER,
    DOMAIN,
    PLATFORMS,
    SERVICE_NEW_WORD,
    SERVICE_REFRESH,
    STORAGE_VERSION,
    VERSION,
)
from .coordinator import WordnikDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

_CARD_URL = f"/{DOMAIN}/wordnik-card.js"
_FRONTEND_KEY = f"{DOMAIN}_frontend_registered"
_AUDIO_KEY = f"{DOMAIN}_audio_registered"
_SERVICES_KEY = f"{DOMAIN}_services_registered"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Wordnik tier from a config entry."""
    session = async_get_clientsession(hass)
    api = WordnikApiClient(session, entry.data[CONF_API_KEY])
    store = Store(hass, STORAGE_VERSION, f"{DOMAIN}_{entry.entry_id}")
    coordinator = WordnikDataUpdateCoordinator(
        hass, entry, api, store, entry.data[CONF_TIER]
    )

    # Register the bundled card, audio cache and services before the first data
    # fetch so the frontend resource is always served even if a fetch fails.
    await _async_register_frontend(hass)
    await _async_register_audio_cache(hass)
    _async_register_services(hass)

    await coordinator.async_load_stored()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    hour, minute, second = coordinator._rollover()  # noqa: SLF001
    unsub = async_track_time_change(
        hass,
        lambda _now: hass.async_create_task(coordinator.async_request_refresh()),
        hour=hour,
        minute=minute,
        second=second,
    )
    entry.async_on_unload(unsub)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Serve and register the bundled Lovelace card once."""
    if hass.data.get(_FRONTEND_KEY):
        return
    hass.data[_FRONTEND_KEY] = True

    path = hass.config.path(f"custom_components/{DOMAIN}/www/wordnik-card.js")
    await hass.http.async_register_static_paths(
        [StaticPathConfig(_CARD_URL, path, False)]
    )
    add_extra_js_url(hass, f"{_CARD_URL}?v={VERSION}")


async def _async_register_audio_cache(hass: HomeAssistant) -> None:
    """Ensure the audio cache directory exists and is served over HTTP."""
    if hass.data.get(_AUDIO_KEY):
        return
    hass.data[_AUDIO_KEY] = True

    cache_dir = hass.config.path(AUDIO_CACHE_DIRNAME)
    await hass.async_add_executor_job(lambda: os.makedirs(cache_dir, exist_ok=True))
    await hass.http.async_register_static_paths(
        [StaticPathConfig(AUDIO_URL_BASE, cache_dir, False)]
    )


def _async_register_services(hass: HomeAssistant) -> None:
    """Register the refresh and new_word services once."""
    if hass.data.get(_SERVICES_KEY):
        return
    hass.data[_SERVICES_KEY] = True

    def _targets(call: ServiceCall) -> list[WordnikDataUpdateCoordinator]:
        entry_ids: set[str] = set()
        dev_reg = dr.async_get(hass)
        ent_reg = er.async_get(hass)
        for device_id in cv.ensure_list(call.data.get("device_id")):
            device = dev_reg.async_get(device_id)
            if device:
                entry_ids.update(device.config_entries)
        for entity_id in cv.ensure_list(call.data.get("entity_id")):
            entity = ent_reg.async_get(entity_id)
            if entity and entity.config_entry_id:
                entry_ids.add(entity.config_entry_id)
        coordinators: dict[str, WordnikDataUpdateCoordinator] = hass.data.get(DOMAIN, {})
        if entry_ids:
            return [coordinators[e] for e in entry_ids if e in coordinators]
        return list(coordinators.values())

    async def _handle_refresh(call: ServiceCall) -> None:
        for coordinator in _targets(call):
            await coordinator.async_request_refresh()

    async def _handle_new_word(call: ServiceCall) -> None:
        for coordinator in _targets(call):
            await coordinator.async_request_new_word()

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, _handle_refresh)
    hass.services.async_register(DOMAIN, SERVICE_NEW_WORD, _handle_new_word)
