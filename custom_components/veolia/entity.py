"""Base entity classes for the Veolia integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PORTAL_URL, DOMAIN, NAME
from .coordinator import VeoliaDataUpdateCoordinator
from .veolia_api.portals import DEFAULT_PORTAL_URL

if TYPE_CHECKING:
    from .data import VeoliaConfigEntry


class VeoliaBaseEntity(CoordinatorEntity[VeoliaDataUpdateCoordinator]):
    """Base entity attached to the Veolia subscription device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VeoliaDataUpdateCoordinator,
        config_entry: VeoliaConfigEntry | None = None,
    ) -> None:
        """Initialize the entity and its device information."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self.config_entry = entry
        portal = entry.data.get(CONF_PORTAL_URL) or DEFAULT_PORTAL_URL
        data = coordinator.data
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=NAME,
            name=f"{NAME} {data.id_abonnement}",
            entry_type=DeviceEntryType.SERVICE,
            serial_number=data.numero_compteur,
            configuration_url=f"https://{portal}",
        )


class VeoliaEntity(VeoliaBaseEntity, SensorEntity):
    """Base Veolia sensor entity (no forced device_class)."""


class VeoliaMesurements(VeoliaEntity):
    """Base entity for Veolia water measurements."""

    _attr_device_class = SensorDeviceClass.WATER
