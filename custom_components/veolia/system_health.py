"""System health for the Veolia integration."""

from __future__ import annotations

from typing import Any

from veolia_api.portals import DEFAULT_PORTAL_URL

from homeassistant.components import system_health
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback

from .const import CONF_PORTAL_URL, DOMAIN
from .data import VeoliaConfigEntry


@callback
def async_register(
    hass: HomeAssistant, register: system_health.SystemHealthRegistration
) -> None:
    """Register the system health info callback."""
    register.async_register_info(system_health_info)


async def system_health_info(hass: HomeAssistant) -> dict[str, Any]:
    """Report configured accounts, refresh health and portal reachability."""
    entries: list[VeoliaConfigEntry] = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]
    portal = DEFAULT_PORTAL_URL
    if entries:
        portal = entries[0].data.get(CONF_PORTAL_URL) or DEFAULT_PORTAL_URL
    return {
        "configured_accounts": len(entries),
        "last_update_success": all(
            entry.runtime_data.last_update_success for entry in entries
        ),
        "can_reach_server": system_health.async_check_can_reach_url(
            hass, f"https://{portal}"
        ),
    }
