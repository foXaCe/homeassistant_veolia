"""Binary sensor platform for Veolia."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory

from .entity import VeoliaBaseEntity
from .helpers import is_unoccupied_mode

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .data import VeoliaConfigEntry
    from .veolia_api.model import AlertSettings

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class VeoliaBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Description of a Veolia alert binary sensor."""

    is_on_fn: Callable[[AlertSettings], bool]
    available_fn: Callable[[AlertSettings], bool] = lambda _settings: True


BINARY_SENSORS: tuple[VeoliaBinarySensorEntityDescription, ...] = (
    VeoliaBinarySensorEntityDescription(
        key="daily_alert_binary_sensor",
        translation_key="daily_alert_binary_sensor",
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda settings: bool(settings.daily_enabled),
        available_fn=lambda settings: not is_unoccupied_mode(settings),
    ),
    VeoliaBinarySensorEntityDescription(
        key="monthly_alert_binary_sensor",
        translation_key="monthly_alert_binary_sensor",
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda settings: bool(settings.monthly_enabled),
        available_fn=lambda settings: not is_unoccupied_mode(settings),
    ),
    VeoliaBinarySensorEntityDescription(
        key="unoccupied_alert_binary_sensor",
        translation_key="unoccupied_alert_binary_sensor",
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=is_unoccupied_mode,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VeoliaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Veolia binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        VeoliaBinarySensor(coordinator, description) for description in BINARY_SENSORS
    )


class VeoliaBinarySensor(VeoliaBaseEntity, BinarySensorEntity):
    """Veolia alert binary sensor driven by its entity description."""

    entity_description: VeoliaBinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return the alert state."""
        settings = self.coordinator.data.alert_settings
        if settings is None:
            return None
        return self.entity_description.is_on_fn(settings)

    @property
    def available(self) -> bool:
        """Combine coordinator health with alert-specific availability."""
        settings = self.coordinator.data.alert_settings
        return (
            super().available
            and settings is not None
            and self.entity_description.available_fn(settings)
        )
