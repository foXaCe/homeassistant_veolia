"""The Veolia integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import VeoliaDataUpdateCoordinator
from .data import VeoliaConfigEntry

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
]

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Veolia integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: VeoliaConfigEntry) -> bool:
    """Set up Veolia from a config entry."""
    coordinator = VeoliaDataUpdateCoordinator(hass)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: VeoliaConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: VeoliaConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Remove a config entry from a device."""
    return True
