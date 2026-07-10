"""Tests for the Veolia switch platform."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.veolia.const import DOMAIN
from custom_components.veolia.switch import SWITCHES, VeoliaSwitch
from custom_components.veolia.veolia_api.exceptions import VeoliaAPISetDataError
from homeassistant.components.recorder import Recorder
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .const import MOCK_ACCOUNT_ID, build_alert_settings


def _entity_id(entity_registry: er.EntityRegistry, key: str) -> str:
    """Resolve the entity_id for a switch key from its unique_id."""
    entity_id = entity_registry.async_get_entity_id(
        "switch", DOMAIN, f"{MOCK_ACCOUNT_ID}_{key}"
    )
    assert entity_id is not None, f"No entity registered for key {key}"
    return entity_id


async def _enable_switch(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    entry: MockConfigEntry,
    key: str,
) -> str:
    """Enable a disabled-by-default switch and reload the entry."""
    entity_id = _entity_id(entity_registry, key)
    entity_registry.async_update_entity(entity_id, disabled_by=None)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    return entity_id


async def test_daily_sms_switch_is_on(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """The daily SMS switch reflects the current alert settings."""
    mock_veolia_api.account_data.alert_settings = build_alert_settings(
        daily_enabled=True, daily_notif_sms=True
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = await _enable_switch(
        hass, entity_registry, mock_config_entry, "daily_sms_alert_switch"
    )
    assert hass.states.get(entity_id).state == STATE_ON


async def test_switches_entity_category_and_default_disabled(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """SMS switches are disabled by default; unoccupied switch is enabled."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    for key in ("daily_sms_alert_switch", "monthly_sms_alert_switch"):
        entry = entity_registry.async_get(_entity_id(entity_registry, key))
        assert entry.entity_category is EntityCategory.CONFIG
        assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION

    unoccupied_entry = entity_registry.async_get(
        _entity_id(entity_registry, "unoccupied_alert_switch")
    )
    assert unoccupied_entry.disabled_by is None


async def test_daily_sms_switch_turn_on_payload(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """Turning on the daily SMS switch pushes the exact enable payload."""
    mock_veolia_api.account_data.alert_settings = build_alert_settings(
        daily_enabled=True, daily_notif_sms=False
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = await _enable_switch(
        hass, entity_registry, mock_config_entry, "daily_sms_alert_switch"
    )

    await hass.services.async_call(
        "switch",
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    mock_veolia_api.set_alerts_settings.assert_awaited()
    pushed = mock_veolia_api.set_alerts_settings.call_args.args[0]
    assert pushed.daily_notif_sms is True


async def test_daily_sms_switch_turn_off_payload(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """Turning off the daily SMS switch pushes the exact disable payload."""
    mock_veolia_api.account_data.alert_settings = build_alert_settings(
        daily_enabled=True, daily_notif_sms=True
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = await _enable_switch(
        hass, entity_registry, mock_config_entry, "daily_sms_alert_switch"
    )

    await hass.services.async_call(
        "switch",
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    mock_veolia_api.set_alerts_settings.assert_awaited()
    pushed = mock_veolia_api.set_alerts_settings.call_args.args[0]
    assert pushed.daily_notif_sms is False


async def test_unoccupied_switch_turn_on_off_payloads(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """The unoccupied switch pushes the daily-threshold-zero on/off payloads."""
    mock_veolia_api.account_data.alert_settings = build_alert_settings(
        daily_enabled=False, daily_threshold=150
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = _entity_id(entity_registry, "unoccupied_alert_switch")
    assert hass.states.get(entity_id).state == STATE_OFF

    await hass.services.async_call(
        "switch", SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    pushed_on = mock_veolia_api.set_alerts_settings.call_args.args[0]
    assert pushed_on.daily_enabled is True
    assert pushed_on.daily_threshold == 0
    assert pushed_on.daily_notif_sms is True
    assert pushed_on.daily_notif_email is True

    await hass.services.async_call(
        "switch", SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    pushed_off = mock_veolia_api.set_alerts_settings.call_args.args[0]
    assert pushed_off.daily_enabled is False


async def test_switch_is_on_none_when_settings_unavailable(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """is_on returns None directly when alert_settings is unavailable."""
    mock_veolia_api.account_data.alert_settings = None
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    entity = VeoliaSwitch(coordinator, SWITCHES[0])
    assert entity.is_on is None


async def test_switch_turn_on_raises_on_api_failure(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """A rejected settings update surfaces as a HomeAssistantError service call error."""
    mock_veolia_api.account_data.alert_settings = build_alert_settings(
        daily_enabled=False
    )
    mock_veolia_api.set_alerts_settings.side_effect = VeoliaAPISetDataError("rejected")
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = _entity_id(entity_registry, "unoccupied_alert_switch")

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "switch", SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True
        )
