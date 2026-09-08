"""Button entities for the Wordnik integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_TIER, DOMAIN, TIERS
from .coordinator import WordnikDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Wordnik new-word button."""
    coordinator: WordnikDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WordnikNewWordButton(coordinator, entry)])


class WordnikNewWordButton(
    CoordinatorEntity[WordnikDataUpdateCoordinator], ButtonEntity
):
    """Button that picks a fresh word for the configured tier."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:refresh"
    _attr_translation_key = "new_word"

    def __init__(
        self, coordinator: WordnikDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialise the button."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_new_word"
        tier = entry.data[CONF_TIER]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Wordnik – {TIERS[tier]['name']}",
            manufacturer="Wordnik",
            model=TIERS[tier]["name"],
        )

    async def async_press(self) -> None:
        """Pick and publish a fresh word."""
        await self.coordinator.async_request_new_word()