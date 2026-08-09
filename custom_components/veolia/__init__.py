"""The Veolia integration."""

from __future__ import annotations

import asyncio

import aiohttp
from veolia_api import VeoliaAPI
from veolia_api.exceptions import VeoliaAPIError
from veolia_api.portals import VEOLIA_PORTAL_CLIENTS

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_PORTAL_URL,
    DOMAIN,
    INITIAL_REFRESH_BACKOFF,
    INITIAL_REFRESH_RETRIES,
    LOGGER,
)
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
    portal_url = entry.data.get(CONF_PORTAL_URL)
    issue_id = f"unknown_portal_{entry.entry_id}"
    if portal_url is not None and portal_url not in VEOLIA_PORTAL_CLIENTS:
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key="unknown_portal",
            translation_placeholders={"portal": portal_url},
        )
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="unknown_portal",
            translation_placeholders={"portal": portal_url},
        )
    ir.async_delete_issue(hass, DOMAIN, issue_id)

    coordinator = VeoliaDataUpdateCoordinator(hass, entry)
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Fetch the initial data in the background: awaiting it here would block
    # boot on the Veolia network round-trip (login + fetch), while the
    # entities are fully functional as soon as the data lands. Errors are
    # handled by the task below (reauth / bounded retries).
    entry.async_create_background_task(
        hass,
        _async_initial_refresh(coordinator),
        "veolia initial refresh",
    )
    return True


async def _async_initial_refresh(coordinator: VeoliaDataUpdateCoordinator) -> None:
    """Run the first data refresh without blocking entry setup.

    Entities are registered immediately and stay unavailable until the
    first data arrives. Invalid credentials start the reauth flow (the
    coordinator handles that internally during ``async_refresh``); a
    transient failure is retried with a short backoff so a momentary
    outage at boot does not leave the integration without data until the
    next scheduled scan interval.
    """
    for attempt in range(INITIAL_REFRESH_RETRIES + 1):
        await coordinator.async_refresh()
        if coordinator.last_update_success:
            return
        if isinstance(coordinator.last_exception, ConfigEntryAuthFailed):
            # The reauth flow was already started by the coordinator.
            return
        if attempt == INITIAL_REFRESH_RETRIES:
            LOGGER.error(
                "Initial Veolia data refresh failed after %d attempts; "
                "retrying at the next scan interval",
                INITIAL_REFRESH_RETRIES + 1,
            )
            return
        await asyncio.sleep(INITIAL_REFRESH_BACKOFF)


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
        LOGGER.info("Migrating config entry %s from version 1 to 2", entry.entry_id)
        api = VeoliaAPI(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            session=async_get_clientsession(hass),
            portal_url=entry.data.get(CONF_PORTAL_URL),
        )
        try:
            login_ok = await api.login()
        except (VeoliaAPIError, aiohttp.ClientError, TimeoutError) as err:
            LOGGER.error(
                "Cannot migrate %s: Veolia login failed (%s); will retry on "
                "next restart",
                entry.entry_id,
                err,
            )
            return False
        if not login_ok or not api.account_data.id_abonnement:
            LOGGER.error(
                "Cannot migrate %s: Veolia account id unavailable; will retry "
                "on next restart",
                entry.entry_id,
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
            entry.entry_id,
            account_id,
        )

    return True
