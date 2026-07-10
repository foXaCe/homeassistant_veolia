"""Base entity classes for the Veolia integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from veolia_api.portals import DEFAULT_PORTAL_URL

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PORTAL_URL, DOMAIN, NAME
from .coordinator import VeoliaDataUpdateCoordinator

if TYPE_CHECKING:
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
            serial_number=data.numero_compteur,
            configuration_url=f"https://{portal}",
        )
