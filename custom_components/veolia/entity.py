"""VeoliaEntity class."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME


class VeoliaEntity(CoordinatorEntity, SensorEntity):
    """Base Veolia sensor entity (no forced device_class)."""

    def __init__(self, coordinator, config_entry) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.config_entry = config_entry

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""
        return True

    @property
    def device_info(self) -> dict:
        """Return device registry information for this entity."""
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "manufacturer": NAME,
            "name": f"{NAME} {self.coordinator.data.id_abonnement}",
        }


class VeoliaMesurements(VeoliaEntity):
    """Representation of a Veolia water measurement entity."""

    @property
    def device_class(self) -> str:
        """Return the device_class of the sensor."""
        return SensorDeviceClass.WATER
