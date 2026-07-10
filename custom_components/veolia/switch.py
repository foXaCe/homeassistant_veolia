"""Switch platform for Veolia."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
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
class VeoliaSwitchEntityDescription(SwitchEntityDescription):
    """Description of a Veolia alert switch."""

    is_on_fn: Callable[[AlertSettings], bool]
    available_fn: Callable[[AlertSettings], bool] = lambda _settings: True
    turn_on_settings: Mapping[str, bool | int]
    turn_off_settings: Mapping[str, bool | int]


SWITCHES: tuple[VeoliaSwitchEntityDescription, ...] = (
    VeoliaSwitchEntityDescription(
        key="daily_sms_alert_switch",
        translation_key="daily_sms_alert_switch",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        is_on_fn=lambda settings: bool(settings.daily_notif_sms),
        available_fn=lambda settings: (
            not is_unoccupied_mode(settings) and bool(settings.daily_enabled)
        ),
        turn_on_settings={"daily_notif_sms": True},
        turn_off_settings={"daily_notif_sms": False},
    ),
    VeoliaSwitchEntityDescription(
        key="monthly_sms_alert_switch",
        translation_key="monthly_sms_alert_switch",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        is_on_fn=lambda settings: bool(settings.monthly_notif_sms),
        available_fn=lambda settings: (
            not is_unoccupied_mode(settings) and bool(settings.monthly_enabled)
        ),
        turn_on_settings={"monthly_notif_sms": True},
        turn_off_settings={"monthly_notif_sms": False},
    ),
    VeoliaSwitchEntityDescription(
        key="unoccupied_alert_switch",
        translation_key="unoccupied_alert_switch",
        entity_category=EntityCategory.CONFIG,
        is_on_fn=is_unoccupied_mode,
        turn_on_settings={
            "daily_enabled": True,
            "daily_threshold": 0,
            "daily_notif_sms": True,
            "daily_notif_email": True,
        },
        turn_off_settings={"daily_enabled": False},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VeoliaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Veolia switches."""
    coordinator = entry.runtime_data
    async_add_entities(
        VeoliaSwitch(coordinator, description) for description in SWITCHES
    )


class VeoliaSwitch(VeoliaBaseEntity, SwitchEntity):
    """Veolia alert switch driven by its entity description."""

    entity_description: VeoliaSwitchEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return the switch state."""
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

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.async_set_alert_settings(
            **self.entity_description.turn_on_settings
        )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.async_set_alert_settings(
            **self.entity_description.turn_off_settings
        )
        self.async_write_ha_state()
