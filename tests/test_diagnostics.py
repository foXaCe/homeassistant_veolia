"""Tests for the Veolia diagnostics platform."""

from __future__ import annotations

from unittest.mock import MagicMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.veolia.diagnostics import async_get_config_entry_diagnostics
from custom_components.veolia.veolia_api.exceptions import VeoliaAPIError
from homeassistant.components.diagnostics.const import REDACTED
from homeassistant.components.recorder import Recorder
from homeassistant.core import HomeAssistant

from .const import MOCK_PASSWORD, MOCK_USERNAME


async def test_diagnostics_redacts_sensitive_fields(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """Sensitive fields are redacted; statistics series are summarized."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    # Entry-level credentials are redacted.
    assert diagnostics["entry"]["data"]["username"] == REDACTED
    assert diagnostics["entry"]["data"]["password"] == REDACTED

    # No plaintext credential leaks anywhere in the payload.
    serialized = repr(diagnostics)
    assert MOCK_USERNAME not in serialized
    assert MOCK_PASSWORD not in serialized

    # Account-data sensitive identifiers are redacted.
    account_data = diagnostics["account_data"]
    for field in (
        "id_abonnement",
        "numero_pds",
        "contact_id",
        "tiers_id",
        "numero_compteur",
        "numero_client",
        "titulaire",
        "adresse_de_branchement",
        "billing_plan",
    ):
        assert account_data[field] == REDACTED

    # Non-sensitive fields remain in clear.
    assert account_data["marque"] == "ITRON"

    # Statistics series are summarized as counts, not dumped in full.
    computed = diagnostics["computed"]
    assert computed["daily_stats_liters"].endswith("rows")
    assert computed["monthly_stats_cubic_meters"].endswith("rows")
    assert computed["index_stats_m3"].endswith("rows")

    assert diagnostics["last_update_success"] is True


async def test_diagnostics_reports_update_failure(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """last_update_success reflects a failed coordinator refresh."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    mock_veolia_api.fetch_all_data.side_effect = VeoliaAPIError("boom")
    await mock_config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)
    assert diagnostics["last_update_success"] is False
