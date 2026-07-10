"""Text platform for Veolia alert thresholds."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.text import TextEntity, TextEntityDescription
from homeassistant.const import EntityCategory

from .entity import VeoliaBaseEntity
from .helpers import is_unoccupied_mode

if TYPE_CHECKING:
    from veolia_api.model import AlertSettings

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .data import VeoliaConfigEntry

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class VeoliaTextEntityDescription(TextEntityDescription):
    """Description of a Veolia alert-threshold text entity."""

    value_fn: Callable[[AlertSettings], str]
    enable_settings_fn: Callable[[int], Mapping[str, bool | int]]
    disable_settings: Mapping[str, bool | int]


TEXTS: tuple[VeoliaTextEntityDescription, ...] = (
    VeoliaTextEntityDescription(
        key="daily_threshold_text",
        translation_key="daily_threshold_text",
        entity_category=EntityCategory.CONFIG,
        native_min=1,
        native_max=6,
        pattern="^(?:0|[1-9][0-9]{2,3}|10000)$",
        value_fn=lambda settings: str(settings.daily_threshold or 0),
        enable_settings_fn=lambda threshold: {
            "daily_enabled": True,
            "daily_threshold": threshold,
            "daily_notif_email": True,
            "daily_notif_sms": False,
        },
        disable_settings={"daily_enabled": False},
    ),
    VeoliaTextEntityDescription(
        key="monthly_threshold_text",
        translation_key="monthly_threshold_text",
        entity_category=EntityCategory.CONFIG,
        native_min=1,
        native_max=4,
        pattern="^(?:0|[1-9][0-9]{0,2}|1000)$",
        value_fn=lambda settings: str(settings.monthly_threshold or 0),
        enable_settings_fn=lambda threshold: {
            "monthly_enabled": True,
            "monthly_threshold": threshold,
            "monthly_notif_email": True,
            "monthly_notif_sms": False,
        },
        disable_settings={"monthly_enabled": False},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VeoliaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Veolia threshold text entities."""
    coordinator = entry.runtime_data
    async_add_entities(VeoliaText(coordinator, description) for description in TEXTS)


class VeoliaText(VeoliaBaseEntity, TextEntity):
    """Veolia alert-threshold text entity driven by its entity description."""

    entity_description: VeoliaTextEntityDescription

    @property
    def native_value(self) -> str | None:
        """Return the current threshold value."""
        settings = self.coordinator.data.alert_settings
        if settings is None:
            return None
        return self.entity_description.value_fn(settings)

    @property
    def available(self) -> bool:
        """Combine coordinator health with alert-specific availability."""
        settings = self.coordinator.data.alert_settings
        return (
            super().available
            and settings is not None
            and not is_unoccupied_mode(settings)
        )

    async def async_set_value(self, value: str) -> None:
        """Set the threshold; zero disables the alert."""
        threshold = int(value)
        if threshold == 0:
            changes = self.entity_description.disable_settings
        else:
            changes = self.entity_description.enable_settings_fn(threshold)
        await self.coordinator.async_set_alert_settings(**changes)
        self.async_write_ha_state()
