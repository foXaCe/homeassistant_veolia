"""Tests for the Veolia sensor platform."""

from __future__ import annotations

from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry
from veolia_api.exceptions import VeoliaAPIError

from custom_components.veolia.const import DOMAIN
from homeassistant.components.recorder import Recorder
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import MOCK_ACCOUNT_ID


def _entity_id(entity_registry: er.EntityRegistry, key: str) -> str:
    """Resolve the entity_id for a sensor key from its unique_id."""
    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{MOCK_ACCOUNT_ID}_{key}"
    )
    assert entity_id is not None, f"No entity registered for key {key}"
    return entity_id


async def test_all_sensors_values_and_attributes(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """All 9 sensors expose the expected state and attributes."""
    freezer.move_to("2026-07-08 12:00:00")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)

    last_index = hass.states.get(_entity_id(entity_registry, "last_index"))
    assert last_index.state == "337.2"
    assert last_index.attributes["data_type"] == "MESURE"
    assert last_index.attributes["last_report"] == "2026-07-08"

    daily_consumption = hass.states.get(
        _entity_id(entity_registry, "daily_consumption")
    )
    assert daily_consumption.state == "120"
    assert daily_consumption.attributes["data_type"] == "MESURE"
    assert daily_consumption.attributes["reading_date"] == "2026-07-08"
    assert daily_consumption.attributes["today"] == 120

    monthly_consumption = hass.states.get(
        _entity_id(entity_registry, "monthly_consumption")
    )
    assert monthly_consumption.state == "3.4"
    assert monthly_consumption.attributes["data_type"] == "MESURE"

    annual_consumption = hass.states.get(
        _entity_id(entity_registry, "annual_consumption")
    )
    assert annual_consumption.state == "6.6"

    last_date = hass.states.get(_entity_id(entity_registry, "last_date"))
    assert last_date.state == "2026-07-08"

    balance = hass.states.get(_entity_id(entity_registry, "balance"))
    assert balance.state == "12.5"

    monthly_payment = hass.states.get(_entity_id(entity_registry, "monthly_payment"))
    assert monthly_payment.state == "45.0"

    next_payment = hass.states.get(_entity_id(entity_registry, "next_payment"))
    assert next_payment.state == "15/07/2026"
    assert next_payment.attributes["date"] == "2026-07-15"
    assert next_payment.attributes["amount"] == 45.0

    billing_index = hass.states.get(_entity_id(entity_registry, "billing_index"))
    assert billing_index.state == "337.0"
    assert billing_index.attributes["reading_date"] == "2026-07-08"
    assert billing_index.attributes["reading_mode"] == "TELERELEVE"
    assert billing_index.attributes["payment_mode"] == "PRELEVEMENT"
    assert billing_index.attributes["contract"] == "Contrat eau"
    assert billing_index.attributes["meter_location"] == "Cave"
    assert billing_index.attributes["status"] == "ACTIF"
    assert billing_index.attributes["brand"] == "ITRON"
    for pii_attribute in (
        "meter_number",
        "branch_address",
        "customer_number",
        "holder",
    ):
        assert pii_attribute not in billing_index.attributes


async def test_sensor_unique_id_pattern(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """Every sensor unique_id follows the {account_id}_{key} pattern."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    expected_keys = {
        "last_index",
        "daily_consumption",
        "monthly_consumption",
        "annual_consumption",
        "last_date",
        "balance",
        "monthly_payment",
        "next_payment",
        "billing_index",
    }
    entries = er.async_entries_for_config_entry(
        entity_registry, mock_config_entry.entry_id
    )
    sensor_entries = [e for e in entries if e.domain == "sensor"]
    assert len(sensor_entries) == 9
    for entry in sensor_entries:
        assert entry.unique_id.startswith(f"{MOCK_ACCOUNT_ID}_")
        key = entry.unique_id.removeprefix(f"{MOCK_ACCOUNT_ID}_")
        assert key in expected_keys


async def test_sensors_unavailable_when_update_failed(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """Sensors become unavailable when the coordinator's last update failed."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = _entity_id(entity_registry, "last_index")
    assert hass.states.get(entity_id).state != STATE_UNAVAILABLE

    mock_veolia_api.fetch_all_data.side_effect = VeoliaAPIError("boom")
    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE


async def test_billing_index_unknown_on_non_numeric_value(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """A non-numeric dernier_index_releve degrades to an unknown state, not a crash."""
    mock_veolia_api.account_data.dernier_index_releve = "not-a-number"
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = _entity_id(entity_registry, "billing_index")
    assert hass.states.get(entity_id).state == "unknown"
