"""Sensor entities for the Wordnik integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SHOW_PRONUNCIATION, CONF_TIER, DEFAULT_SHOW_PRONUNCIATION, DOMAIN, TIERS
from .coordinator import WordnikDataUpdateCoordinator

_MAX_STATE_LEN = 255


@dataclass(frozen=True, kw_only=True)
class WordnikSensorDescription(SensorEntityDescription):
    """Describes a Wordnik sensor."""

    value_fn: Callable[[dict], str | None]
    attributes_fn: Callable[[dict], dict] = lambda _data: {}


SENSOR_TYPES: tuple[WordnikSensorDescription, ...] = (
    WordnikSensorDescription(
        key="word",
        translation_key="word",
        icon="mdi:book-alphabet",
        value_fn=lambda data: data.get("word"),
        attributes_fn=lambda data: {
            "part_of_speech": data.get("part_of_speech"),
            "tier": data.get("tier"),
            "tier_name": data.get("tier_name"),
            "date": data.get("date"),
            "word_url": data.get("word_url"),
            "attribution": data.get("attribution"),
        },
    ),
    WordnikSensorDescription(
        key="definition",
        translation_key="definition",
        icon="mdi:text-box-outline",
        value_fn=lambda data: data.get("definition"),
        attributes_fn=lambda data: {
            "definitions": data.get("definitions"),
            "source_dictionary": data.get("source_dictionary"),
            "attribution": data.get("attribution"),
        },
    ),
    WordnikSensorDescription(
        key="example",
        translation_key="example",
        icon="mdi:format-quote-close",
        value_fn=lambda data: data.get("example"),
        attributes_fn=lambda data: {"examples": data.get("examples")},
    ),
    WordnikSensorDescription(
        key="audio",
        translation_key="audio",
        icon="mdi:volume-high",
        value_fn=lambda data: data.get("audio_url"),
        attributes_fn=lambda data: {
            "duration": data.get("audio_duration"),
            "audio": data.get("audio"),
        },
    ),
)

PRONUNCIATION_SENSOR = WordnikSensorDescription(
    key="pronunciation",
    translation_key="pronunciation",
    icon="mdi:microphone-message",
    value_fn=lambda data: data.get("pronunciation"),
    attributes_fn=lambda data: {
        "type": data.get("pronunciation_type"),
        "pronunciations": data.get("pronunciations"),
    },
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Wordnik sensors."""
    coordinator: WordnikDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    descriptions = list(SENSOR_TYPES)
    if entry.options.get(CONF_SHOW_PRONUNCIATION, DEFAULT_SHOW_PRONUNCIATION):
        descriptions.append(PRONUNCIATION_SENSOR)

    async_add_entities(
        WordnikSensor(coordinator, entry, description) for description in descriptions
    )


class WordnikSensor(CoordinatorEntity[WordnikDataUpdateCoordinator], SensorEntity):
    """A single Wordnik sensor."""

    entity_description: WordnikSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WordnikDataUpdateCoordinator,
        entry: ConfigEntry,
        description: WordnikSensorDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        tier = entry.data[CONF_TIER]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Wordnik – {TIERS[tier]['name']}",
            manufacturer="Wordnik",
            model=TIERS[tier]["name"],
        )

    @property
    def _data(self) -> dict:
        return self.coordinator.data or {}

    @property
    def native_value(self) -> str | None:
        """Return the sensor state, truncated to the HA limit."""
        value = self.entity_description.value_fn(self._data)
        if isinstance(value, str) and len(value) > _MAX_STATE_LEN:
            return value[: _MAX_STATE_LEN - 1] + "…"
        return value

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        return {
            key: value
            for key, value in self.entity_description.attributes_fn(self._data).items()
            if value is not None
        }
