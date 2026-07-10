"""Tests for the Veolia binary_sensor platform."""

from __future__ import annotations

from unittest.mock import MagicMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.veolia.binary_sensor import BINARY_SENSORS, VeoliaBinarySensor
from custom_components.veolia.const import DOMAIN
from homeassistant.components.recorder import Recorder
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import MOCK_ACCOUNT_ID, build_alert_settings


def _entity_id(entity_registry: er.EntityRegistry, key: str) -> str:
    """Resolve the entity_id for a binary_sensor key from its unique_id."""
    entity_id = entity_registry.async_get_entity_id(
        "binary_sensor", DOMAIN, f"{MOCK_ACCOUNT_ID}_{key}"
    )
    assert entity_id is not None, f"No entity registered for key {key}"
    return entity_id


async def test_daily_and_monthly_alert_on_off(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """The daily/monthly alert binary sensors reflect the alert settings."""
    mock_veolia_api.account_data.alert_settings = build_alert_settings(
        daily_enabled=True, daily_threshold=150, monthly_enabled=False
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    daily = hass.states.get(_entity_id(entity_registry, "daily_alert_binary_sensor"))
    monthly = hass.states.get(
        _entity_id(entity_registry, "monthly_alert_binary_sensor")
    )
    assert daily.state == STATE_ON
    assert monthly.state == STATE_OFF


async def test_unoccupied_alert_binary_sensor(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """Unoccupied mode is on when daily is enabled with a zero threshold."""
    mock_veolia_api.account_data.alert_settings = build_alert_settings(
        daily_enabled=True, daily_threshold=0
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    unoccupied = hass.states.get(
        _entity_id(entity_registry, "unoccupied_alert_binary_sensor")
    )
    assert unoccupied.state == STATE_ON

    # And daily/monthly alert sensors become unavailable while in this mode.
    daily = hass.states.get(_entity_id(entity_registry, "daily_alert_binary_sensor"))
    monthly = hass.states.get(
        _entity_id(entity_registry, "monthly_alert_binary_sensor")
    )
    assert daily.state == STATE_UNAVAILABLE
    assert monthly.state == STATE_UNAVAILABLE


async def test_binary_sensors_available_when_not_unoccupied(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """Daily/monthly alert sensors are available outside unoccupied mode."""
    mock_veolia_api.account_data.alert_settings = build_alert_settings(
        daily_enabled=True, daily_threshold=150, monthly_enabled=True
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    daily = hass.states.get(_entity_id(entity_registry, "daily_alert_binary_sensor"))
    assert daily.state != STATE_UNAVAILABLE


async def test_binary_sensors_entity_category_diagnostic(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """All three binary sensors are diagnostic entities."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    for key in (
        "daily_alert_binary_sensor",
        "monthly_alert_binary_sensor",
        "unoccupied_alert_binary_sensor",
    ):
        entry = entity_registry.async_get(_entity_id(entity_registry, key))
        assert entry.entity_category is EntityCategory.DIAGNOSTIC


async def test_binary_sensor_unavailable_when_alert_settings_none(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """When alert_settings is None, is_on returns None (state unknown)."""
    mock_veolia_api.account_data.alert_settings = None
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = _entity_id(entity_registry, "daily_alert_binary_sensor")
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE

    # Direct unit check of the is_on property itself (unreachable through the
    # entity platform since `available` already gates rendering to
    # "unavailable" before `is_on` would ever be evaluated).
    coordinator = mock_config_entry.runtime_data
    entity = VeoliaBinarySensor(coordinator, BINARY_SENSORS[0])
    assert entity.is_on is None
