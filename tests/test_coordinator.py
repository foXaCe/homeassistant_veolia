"""Tests for VeoliaDataUpdateCoordinator."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.veolia.const import DEFAULT_SCAN_INTERVAL_HOURS
from custom_components.veolia.coordinator import VeoliaDataUpdateCoordinator
from custom_components.veolia.model import VeoliaModel
from custom_components.veolia.veolia_api.exceptions import (
    VeoliaAPIError,
    VeoliaAPIInvalidCredentialsError,
)
from homeassistant.components.recorder import Recorder
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import MOCK_ACCOUNT_ID


async def test_coordinator_update_success(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """A successful refresh stores a computed VeoliaModel."""
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)

    await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    assert isinstance(coordinator.data, VeoliaModel)
    assert coordinator.data.id_abonnement == MOCK_ACCOUNT_ID


async def test_coordinator_initial_fetch_uses_one_year_window(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The very first refresh fetches a full year of history."""
    freezer.move_to("2026-07-10")
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)

    await coordinator.async_refresh()

    mock_veolia_api.fetch_all_data.assert_called_once_with(
        date(2025, 7, 1), date(2026, 7, 1)
    )


async def test_coordinator_periodic_fetch_uses_two_month_window(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """After the initial fetch, subsequent refreshes only cover ~2 months."""
    freezer.move_to("2026-07-10")
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)

    await coordinator.async_refresh()
    await coordinator.async_refresh()

    assert mock_veolia_api.fetch_all_data.call_count == 2
    first_call, second_call = mock_veolia_api.fetch_all_data.call_args_list
    assert first_call.args == (date(2025, 7, 1), date(2026, 7, 1))
    assert second_call.args == (date(2026, 6, 1), date(2026, 7, 1))


async def test_coordinator_auth_failed_triggers_reauth(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """Invalid credentials mark the update failed and start a reauth flow."""
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)
    mock_veolia_api.fetch_all_data.side_effect = VeoliaAPIInvalidCredentialsError(
        "bad creds"
    )

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success is False
    flows = hass.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == "reauth"


async def test_coordinator_update_failed_on_api_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """A generic API error is surfaced as UpdateFailed and marks update failed."""
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)
    mock_veolia_api.fetch_all_data.side_effect = VeoliaAPIError("boom")

    await coordinator.async_refresh()

    assert coordinator.last_update_success is False
    assert isinstance(coordinator.last_exception, UpdateFailed)


async def test_update_interval_from_options(
    hass: HomeAssistant,
) -> None:
    """The update interval is read from the config entry options."""
    entry = MockConfigEntry(
        domain="veolia",
        options={CONF_SCAN_INTERVAL: 3},
        data={"username": "a@b.com", "password": "x", "portal_url": None},
    )
    entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, entry)
    assert coordinator.update_interval == timedelta(hours=3)


async def test_update_interval_default(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Without options, the default scan interval is used."""
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)
    assert coordinator.update_interval == timedelta(hours=DEFAULT_SCAN_INTERVAL_HOURS)


async def test_async_set_alert_settings_success_pushes_and_refreshes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """A successful settings change mutates data, pushes it and refreshes."""
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)
    await coordinator.async_refresh()
    assert mock_veolia_api.fetch_all_data.call_count == 1

    await coordinator.async_set_alert_settings(daily_enabled=True, daily_threshold=200)
    await hass.async_block_till_done()

    assert coordinator.data.alert_settings.daily_threshold == 200
    mock_veolia_api.set_alerts_settings.assert_awaited_once()
    pushed_settings = mock_veolia_api.set_alerts_settings.call_args.args[0]
    assert pushed_settings.daily_threshold == 200
    # A refresh was requested after the push.
    assert mock_veolia_api.fetch_all_data.call_count == 2

    # The coordinator was created outside of the normal config entry setup
    # lifecycle, so nothing will cancel its debounced-refresh timer for us.
    await coordinator.async_shutdown()


async def test_async_set_alert_settings_rejected_raises(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """A rejected settings update (API returns False) raises HomeAssistantError."""
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)
    await coordinator.async_refresh()
    mock_veolia_api.set_alerts_settings.return_value = False

    with pytest.raises(HomeAssistantError):
        await coordinator.async_set_alert_settings(daily_enabled=False)


async def test_async_set_alert_settings_api_error_raises(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """A VeoliaAPIError while pushing settings raises HomeAssistantError."""
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)
    await coordinator.async_refresh()
    mock_veolia_api.set_alerts_settings.side_effect = VeoliaAPIError("rejected")

    with pytest.raises(HomeAssistantError):
        await coordinator.async_set_alert_settings(daily_enabled=False)


async def test_async_set_alert_settings_unavailable_raises(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """Alert settings unavailable (None) raises HomeAssistantError."""
    mock_veolia_api.account_data.alert_settings = None
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)
    await coordinator.async_refresh()

    with pytest.raises(HomeAssistantError):
        await coordinator.async_set_alert_settings(daily_enabled=True)

    mock_veolia_api.set_alerts_settings.assert_not_called()
