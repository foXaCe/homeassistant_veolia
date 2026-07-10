"""Tests for the Veolia options flow."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.veolia.const import DEFAULT_SCAN_INTERVAL_HOURS
from homeassistant.components.recorder import Recorder
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


async def test_options_flow_shows_default_scan_interval(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """The init step shows the current (or default) scan interval."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    schema = result["data_schema"].schema
    (scan_interval_key,) = (key for key in schema if key == CONF_SCAN_INTERVAL)
    assert scan_interval_key.default() == DEFAULT_SCAN_INTERVAL_HOURS


async def test_options_flow_updates_scan_interval(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """Submitting a new scan interval updates the entry options as an int."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 12}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_SCAN_INTERVAL] == 12
    assert isinstance(mock_config_entry.options[CONF_SCAN_INTERVAL], int)
    # The coordinator's update interval reflects the new option after reload.
    assert mock_config_entry.runtime_data.update_interval == timedelta(hours=12)


async def test_options_flow_shows_previously_saved_value(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_veolia_api: MagicMock,
) -> None:
    """A previously saved scan interval is suggested as the default."""
    entry = MockConfigEntry(
        domain="veolia",
        unique_id="1235075",
        version=2,
        data={"username": "test@example.com", "password": "secret", "portal_url": None},
        options={CONF_SCAN_INTERVAL: 8},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    schema = result["data_schema"].schema
    (scan_interval_key,) = (key for key in schema if key == CONF_SCAN_INTERVAL)
    assert scan_interval_key.default() == 8
