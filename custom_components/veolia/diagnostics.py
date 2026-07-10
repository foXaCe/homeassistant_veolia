"""Diagnostics support for the Veolia integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import VeoliaConfigEntry

TO_REDACT = {
    CONF_PASSWORD,
    CONF_USERNAME,
    "access_token",
    "code",
    "verifier",
    "id_abonnement",
    "numero_pds",
    "contact_id",
    "tiers_id",
    "numero_compteur",
    "numero_client",
    "titulaire",
    "adresse_de_branchement",
    "billing_plan",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: VeoliaConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    account = asdict(coordinator.client_api.account_data)
    computed = asdict(coordinator.data.computed)
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "account_data": async_redact_data(account, TO_REDACT),
        "computed": computed,
        "last_update_success": coordinator.last_update_success,
    }
