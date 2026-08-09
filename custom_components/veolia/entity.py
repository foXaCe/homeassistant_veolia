"""Base entity classes for the Veolia integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast

from veolia_api.portals import DEFAULT_PORTAL_URL

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PORTAL_URL, DOMAIN, NAME
from .coordinator import VeoliaDataUpdateCoordinator

if TYPE_CHECKING:
    from collections.abc import Callable

    from veolia_api.model import AlertSettings

    from homeassistant.helpers.entity import EntityDescription


class VeoliaBaseEntity(CoordinatorEntity[VeoliaDataUpdateCoordinator]):
    """Base entity attached to the Veolia subscription device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VeoliaDataUpdateCoordinator,
        description: EntityDescription,
    ) -> None:
        """Initialize the entity and its device information."""
        super().__init__(coordinator)
        self.entity_description = description
        entry = coordinator.config_entry
        account_id = str(entry.unique_id)
        self._attr_unique_id = f"{account_id}_{description.key}"
        portal = entry.data.get(CONF_PORTAL_URL) or DEFAULT_PORTAL_URL
        data = coordinator.data
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, account_id)},
            manufacturer=NAME,
            name=NAME,
            entry_type=DeviceEntryType.SERVICE,
            # The entity is created before the initial data arrives (setup no
            # longer blocks on the network fetch); the serial number is only
            # known once the first refresh succeeded.
            serial_number=data.numero_compteur if data is not None else None,
            configuration_url=f"https://{portal}",
        )

    @property
    def available(self) -> bool:
        """Return whether the entity is available.

        Requires a healthy coordinator *and* a first successful refresh:
        entities are registered during entry setup, before the background
        initial refresh has completed, so they stay unavailable until data
        is available.
        """
        return super().available and self.coordinator.data is not None


class AlertEntityDescription(Protocol):
    """Description contract for alert-driven entities."""

    @property
    def available_fn(self) -> Callable[[AlertSettings], bool]:
        """Return the predicate deciding entity availability."""
        ...


class VeoliaAlertEntity(VeoliaBaseEntity):
    """Base for entities driven by the account alert settings."""

    @property
    def available(self) -> bool:
        """Combine coordinator health with alert-specific availability."""
        if not super().available:
            return False
        settings = self.coordinator.data.alert_settings
        description = cast("AlertEntityDescription", self.entity_description)
        return settings is not None and description.available_fn(settings)

    async def _async_push_alert_settings(self, **changes: bool | int) -> None:
        """Push alert-settings changes then refresh the entity state."""
        await self.coordinator.async_set_alert_settings(**changes)
        self.async_write_ha_state()
