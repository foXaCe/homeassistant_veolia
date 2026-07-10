"""The Veolia integration."""

from __future__ import annotations

from veolia_api import VeoliaAPI
from veolia_api.exceptions import VeoliaAPIError

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import CONF_PORTAL_URL, DOMAIN, LOGGER
from .coordinator import VeoliaDataUpdateCoordinator
from .data import VeoliaConfigEntry

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: VeoliaConfigEntry) -> bool:
    """Set up Veolia from a config entry."""
    coordinator = VeoliaDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: VeoliaConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: VeoliaConfigEntry) -> bool:
    """Migrate a config entry to the current version.

    Version 1 → 2: unique_ids move from ``{entry_id}_{key}`` to
    ``{account_id}_{key}`` (Veolia subscription id), the device identifier
    follows, and the entry itself gains the account id as unique_id.
    """
    if entry.version > 2:
        # Downgrade from a future version: not supported.
        return False

    if entry.version == 1:
        LOGGER.info("Migrating config entry %s from version 1 to 2", entry.title)
        api = VeoliaAPI(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            session=async_get_clientsession(hass),
            portal_url=entry.data.get(CONF_PORTAL_URL),
        )
        try:
            login_ok = await api.login()
        except VeoliaAPIError as err:
            LOGGER.error(
                "Cannot migrate %s: Veolia login failed (%s); will retry on "
                "next restart",
                entry.title,
                err,
            )
            return False
        if not login_ok or not api.account_data.id_abonnement:
            LOGGER.error(
                "Cannot migrate %s: Veolia account id unavailable; will retry "
                "on next restart",
                entry.title,
            )
            return False
        account_id = str(api.account_data.id_abonnement)
        old_prefix = f"{entry.entry_id}_"
        new_prefix = f"{account_id}_"

        @callback
        def _update_unique_id(
            registry_entry: er.RegistryEntry,
        ) -> dict[str, str] | None:
            if not registry_entry.unique_id.startswith(old_prefix):
                return None
            return {
                "new_unique_id": (
                    new_prefix + registry_entry.unique_id.removeprefix(old_prefix)
                )
            }

        await er.async_migrate_entries(hass, entry.entry_id, _update_unique_id)

        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, entry.entry_id)}
        )
        if device is not None:
            device_registry.async_update_device(
                device.id, new_identifiers={(DOMAIN, account_id)}
            )

        hass.config_entries.async_update_entry(entry, unique_id=account_id, version=2)
        LOGGER.info(
            "Migration of %s to version 2 done (account id %s)",
            entry.title,
            account_id,
        )

    return True
