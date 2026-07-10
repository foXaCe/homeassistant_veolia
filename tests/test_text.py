"""Tests for the Veolia text platform."""

from __future__ import annotations

from unittest.mock import MagicMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.veolia.const import DOMAIN
from custom_components.veolia.text import TEXTS, VeoliaText
from homeassistant.components.recorder import Recorder
from homeassistant.components.text import ATTR_VALUE, SERVICE_SET_VALUE
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import MOCK_ACCOUNT_ID, build_alert_settings


def _entity_id(entity_registry: er.EntityRegistry, key: str) -> str:
    """Resolve the entity_id for a text key from its unique_id."""
    entity_id = entity_registry.async_get_entity_id(
        "text", DOMAIN, f"{MOCK_ACCOUNT_ID}_{key}"
    )
    assert entity_id is not None, f"No entity registered for key {key}"
    return entity_id


async def test_daily_threshold_text_value_and_pattern(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """The daily threshold text reflects the current value and exposes a pattern."""
    mock_veolia_api.account_data.alert_settings = build_alert_settings(
        daily_enabled=True, daily_threshold=150
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = _entity_id(entity_registry, "daily_threshold_text")
    state = hass.states.get(entity_id)
    assert state.state == "150"
    assert state.attributes["pattern"] == "^(?:0|[1-9][0-9]{2,3}|10000)$"
    entry = entity_registry.async_get(entity_id)
    assert entry.entity_category is EntityCategory.CONFIG


async def test_monthly_threshold_text_value(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """The monthly threshold text reflects the current value."""
    mock_veolia_api.account_data.alert_settings = build_alert_settings(
        monthly_enabled=True, monthly_threshold=5
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = _entity_id(entity_registry, "monthly_threshold_text")
    assert hass.states.get(entity_id).state == "5"


async def test_set_value_zero_disables_daily_alert(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """Setting the daily threshold to 0 disables the daily alert."""
    mock_veolia_api.account_data.alert_settings = build_alert_settings(
        daily_enabled=True, daily_threshold=150
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = _entity_id(entity_registry, "daily_threshold_text")

    await hass.services.async_call(
        "text",
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: "0"},
        blocking=True,
    )
    await hass.async_block_till_done()

    pushed = mock_veolia_api.set_alerts_settings.call_args.args[0]
    assert pushed.daily_enabled is False


async def test_set_value_nonzero_enables_daily_alert_with_exact_payload(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """Setting a non-zero daily threshold pushes the exact enable payload."""
    mock_veolia_api.account_data.alert_settings = build_alert_settings(
        daily_enabled=False, daily_threshold=0
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = _entity_id(entity_registry, "daily_threshold_text")

    await hass.services.async_call(
        "text",
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: "200"},
        blocking=True,
    )
    await hass.async_block_till_done()

    pushed = mock_veolia_api.set_alerts_settings.call_args.args[0]
    assert pushed.daily_enabled is True
    assert pushed.daily_threshold == 200
    assert pushed.daily_notif_email is True
    assert pushed.daily_notif_sms is False


async def test_set_value_nonzero_enables_monthly_alert_with_exact_payload(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """Setting a non-zero monthly threshold pushes the exact enable payload."""
    mock_veolia_api.account_data.alert_settings = build_alert_settings(
        monthly_enabled=False, monthly_threshold=0
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = _entity_id(entity_registry, "monthly_threshold_text")

    await hass.services.async_call(
        "text",
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: "10"},
        blocking=True,
    )
    await hass.async_block_till_done()

    pushed = mock_veolia_api.set_alerts_settings.call_args.args[0]
    assert pushed.monthly_enabled is True
    assert pushed.monthly_threshold == 10
    assert pushed.monthly_notif_email is True
    assert pushed.monthly_notif_sms is False


async def test_text_unique_id_pattern(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """Both text entities follow the {account_id}_{key} unique_id pattern."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(
        entity_registry, mock_config_entry.entry_id
    )
    text_entries = [e for e in entries if e.domain == "text"]
    assert len(text_entries) == 2
    for entry in text_entries:
        assert entry.unique_id.startswith(f"{MOCK_ACCOUNT_ID}_")


async def test_text_unavailable_when_unoccupied_mode(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """Threshold texts become unavailable while unoccupied mode is active."""
    mock_veolia_api.account_data.alert_settings = build_alert_settings(
        daily_enabled=True, daily_threshold=0
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = _entity_id(entity_registry, "daily_threshold_text")
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE


async def test_text_native_value_none_when_settings_unavailable(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """native_value returns None directly when alert_settings is unavailable."""
    mock_veolia_api.account_data.alert_settings = None
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    entity = VeoliaText(coordinator, TEXTS[0])
    assert entity.native_value is None
