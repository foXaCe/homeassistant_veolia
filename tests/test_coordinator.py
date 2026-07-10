"""Tests for VeoliaDataUpdateCoordinator."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from veolia_api.exceptions import VeoliaAPIError, VeoliaAPIInvalidCredentialsError
from veolia_api.model import AlertSettings

from custom_components.veolia.const import (
    CONF_COST_PER_M3,
    CONSECUTIVE_FAILURES_FOR_ISSUE,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DOMAIN,
)
from custom_components.veolia.coordinator import (
    VeoliaDataUpdateCoordinator,
    _anchored_series_params,
)
from custom_components.veolia.model import VeoliaModel
from custom_components.veolia.statistics import LastStat, build_statistic_id
from homeassistant.components.recorder import Recorder
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import MOCK_ACCOUNT_ID, MOCK_CONFIG_ENTRY_DATA, build_alert_settings


@pytest.fixture
def mock_statistics_anchor() -> Generator[AsyncMock]:
    """Patch the coordinator's recorder-statistics anchor and import calls.

    These tests instantiate ``VeoliaDataUpdateCoordinator`` directly rather
    than through ``hass.config_entries.async_setup``, so the ``recorder``
    dependency declared in the manifest is never actually set up on
    ``hass``. Patching at the coordinator's import site lets these tests
    exercise the fetch-window and error-handling logic without a real
    in-memory recorder; see test_statistics.py for the recorder-backed
    anchoring/import behavior. Defaults to "no prior statistic" (a full
    year is fetched); set ``return_value``/``side_effect`` per test to
    simulate an anchored series (return a ``LastStat``).
    """
    with (
        patch(
            "custom_components.veolia.coordinator.get_last_stat",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_anchor,
        patch("custom_components.veolia.coordinator.import_volume_statistics"),
    ):
        yield mock_anchor


def test_anchored_series_params_no_anchor() -> None:
    """Without an anchor, the series is imported from scratch."""
    assert _anchored_series_params(None, set()) == (0.0, None)


def test_anchored_series_params_rewinds_one_row() -> None:
    """The cutoff rewinds one day and the sum restarts from before the last row."""
    anchor = LastStat(sum=4200.0, state=120.0, date=date(2026, 7, 5))
    assert _anchored_series_params(anchor, {anchor.date}) == (4080.0, date(2026, 7, 4))


def test_anchored_series_params_state_none_falls_back_to_strict() -> None:
    """A stored row without a state falls back to strict (non-rewound) anchoring."""
    anchor = LastStat(sum=4200.0, state=None, date=date(2026, 7, 5))
    assert _anchored_series_params(anchor, {anchor.date}) == (4200.0, date(2026, 7, 5))


def test_anchored_series_params_missing_anchor_row_falls_back_to_strict() -> None:
    """If the anchor day vanished from the fetch, fall back to strict anchoring.

    Rewinding onto a vanished row would subtract its contribution from the
    running sum without ever re-adding it, making the recorder ``sum``
    regress (see plan 013). The fetch here covers 07-01, 07-02 and 07-04 but
    not the 07-03 anchor day itself.
    """
    anchor = LastStat(sum=450.0, state=200.0, date=date(2026, 7, 3))
    fetched_dates = {date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 4)}
    assert _anchored_series_params(anchor, fetched_dates) == (450.0, date(2026, 7, 3))


def test_anchored_series_params_rewinds_when_anchor_row_present() -> None:
    """When the anchor day is still present in the fetch, rewind as before."""
    anchor = LastStat(sum=450.0, state=200.0, date=date(2026, 7, 3))
    fetched_dates = {date(2026, 7, 2), date(2026, 7, 3), date(2026, 7, 4)}
    assert _anchored_series_params(anchor, fetched_dates) == (250.0, date(2026, 7, 2))


async def test_coordinator_update_success(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    mock_statistics_anchor: AsyncMock,
) -> None:
    """A successful refresh stores a computed VeoliaModel."""
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)

    await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    assert isinstance(coordinator.data, VeoliaModel)
    assert coordinator.data.id_abonnement == MOCK_ACCOUNT_ID


async def test_coordinator_no_anchor_uses_one_year_window(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    mock_statistics_anchor: AsyncMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """With no existing daily-consumption statistic, a full year is fetched."""
    freezer.move_to("2026-07-10")
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)

    await coordinator.async_refresh()

    mock_veolia_api.fetch_all_data.assert_called_once_with(
        date(2025, 7, 1), date(2026, 7, 1)
    )


async def test_coordinator_anchored_window_starts_at_anchor_month(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    mock_statistics_anchor: AsyncMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The fetch window starts at the first of the last-anchored statistic's month."""
    freezer.move_to("2026-07-10")
    mock_statistics_anchor.return_value = LastStat(
        sum=4200.0, state=120.0, date=date(2026, 6, 5)
    )
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)

    await coordinator.async_refresh()

    mock_veolia_api.fetch_all_data.assert_called_once_with(
        date(2026, 6, 1), date(2026, 7, 1)
    )


async def test_coordinator_anchored_window_handles_year_rollover(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    mock_statistics_anchor: AsyncMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The anchored fetch window correctly rolls back across a year boundary."""
    freezer.move_to("2026-01-15")
    mock_statistics_anchor.return_value = LastStat(
        sum=100.0, state=5.0, date=date(2025, 12, 20)
    )
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)

    await coordinator.async_refresh()

    mock_veolia_api.fetch_all_data.assert_called_once_with(
        date(2025, 12, 1), date(2026, 1, 1)
    )


async def test_coordinator_cost_anchor_missing_triggers_full_backfill(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A daily anchor with no cost anchor still triggers a full year backfill.

    Simulates the cost series being added after an integration update: the
    daily-consumption series already has history, but the cost series has
    never been imported yet.
    """
    freezer.move_to("2026-07-10")
    daily_statistic_id = build_statistic_id(MOCK_ACCOUNT_ID, "daily_consumption")
    daily_anchor = LastStat(sum=4200.0, state=120.0, date=date(2026, 6, 5))

    async def _side_effect(_hass: HomeAssistant, statistic_id: str) -> LastStat | None:
        return daily_anchor if statistic_id == daily_statistic_id else None

    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)

    with (
        patch(
            "custom_components.veolia.coordinator.get_last_stat",
            new_callable=AsyncMock,
            side_effect=_side_effect,
        ),
        patch("custom_components.veolia.coordinator.import_volume_statistics"),
    ):
        await coordinator.async_refresh()

    mock_veolia_api.fetch_all_data.assert_called_once_with(
        date(2025, 7, 1), date(2026, 7, 1)
    )


async def test_coordinator_imports_cost_statistics(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """A successful refresh imports the cost series alongside the other three."""
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)

    with (
        patch(
            "custom_components.veolia.coordinator.get_last_stat",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "custom_components.veolia.coordinator.import_volume_statistics"
        ) as mock_import,
    ):
        await coordinator.async_refresh()

    assert mock_import.call_count == 4
    cost_statistic_id = build_statistic_id(MOCK_ACCOUNT_ID, "cost")
    call = next(c for c in mock_import.call_args_list if c.args[1] == cost_statistic_id)
    assert call.args[2] == f"Veolia coût eau {MOCK_ACCOUNT_ID}"
    assert call.args[4] == "EUR"
    assert call.kwargs["unit_class"] is None


async def test_coordinator_cost_price_from_options(
    hass: HomeAssistant,
    mock_veolia_api: MagicMock,
) -> None:
    """The cost series uses the price per m3 configured in the entry options."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id=MOCK_ACCOUNT_ID,
        data=dict(MOCK_CONFIG_ENTRY_DATA),
        options={CONF_COST_PER_M3: 5.0},
    )
    entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, entry)

    with (
        patch(
            "custom_components.veolia.coordinator.get_last_stat",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "custom_components.veolia.coordinator.import_volume_statistics"
        ) as mock_import,
    ):
        await coordinator.async_refresh()

    cost_statistic_id = build_statistic_id(MOCK_ACCOUNT_ID, "cost")
    call = next(c for c in mock_import.call_args_list if c.args[1] == cost_statistic_id)
    stats = call.args[3]
    # Fixture daily data: first row is 2026-07-01 with 100 L.
    assert stats[0]["state"] == pytest.approx(100 / 1000 * 5.0)


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
    assert coordinator.last_exception is not None
    assert coordinator.last_exception.translation_key == "auth_failed"
    flows = hass.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == "reauth"


async def test_coordinator_update_failed_on_api_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    mock_statistics_anchor: AsyncMock,
) -> None:
    """A generic API error is surfaced as UpdateFailed and marks update failed."""
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)
    mock_veolia_api.fetch_all_data.side_effect = VeoliaAPIError("boom")

    await coordinator.async_refresh()

    assert coordinator.last_update_success is False
    assert isinstance(coordinator.last_exception, UpdateFailed)
    assert coordinator.last_exception.translation_key == "update_failed"
    assert coordinator.last_exception.translation_placeholders == {"error": "boom"}


async def test_coordinator_update_failed_on_network_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    mock_statistics_anchor: AsyncMock,
) -> None:
    """A raw network error escaping the client is surfaced as UpdateFailed."""
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)
    mock_veolia_api.fetch_all_data.side_effect = aiohttp.ClientError("boom")

    await coordinator.async_refresh()

    assert coordinator.last_update_success is False
    assert isinstance(coordinator.last_exception, UpdateFailed)


async def test_coordinator_creates_api_down_issue_after_threshold(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    mock_statistics_anchor: AsyncMock,
) -> None:
    """CONSECUTIVE_FAILURES_FOR_ISSUE consecutive failures raise the api_down issue.

    No issue exists before the threshold is reached (anti-flapping): a
    transient blip of fewer failures than the threshold must not create it.
    """
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)
    mock_veolia_api.fetch_all_data.side_effect = VeoliaAPIError("boom")
    issue_id = f"api_down_{mock_config_entry.entry_id}"
    issue_registry = ir.async_get(hass)

    for _ in range(CONSECUTIVE_FAILURES_FOR_ISSUE - 1):
        await coordinator.async_refresh()
        assert issue_registry.async_get_issue(DOMAIN, issue_id) is None

    await coordinator.async_refresh()

    assert issue_registry.async_get_issue(DOMAIN, issue_id) is not None


async def test_coordinator_api_down_issue_cleared_on_success_and_streak_resets(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    mock_statistics_anchor: AsyncMock,
) -> None:
    """A successful refresh clears the api_down issue and resets the failure streak."""
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)
    mock_veolia_api.fetch_all_data.side_effect = VeoliaAPIError("boom")
    issue_id = f"api_down_{mock_config_entry.entry_id}"
    issue_registry = ir.async_get(hass)

    for _ in range(CONSECUTIVE_FAILURES_FOR_ISSUE):
        await coordinator.async_refresh()
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is not None

    mock_veolia_api.fetch_all_data.side_effect = None
    await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is None

    # The streak was reset by the success above: a fresh outage must run
    # through the full threshold again before the issue reappears.
    mock_veolia_api.fetch_all_data.side_effect = VeoliaAPIError("boom again")
    for _ in range(CONSECUTIVE_FAILURES_FOR_ISSUE - 1):
        await coordinator.async_refresh()
        assert issue_registry.async_get_issue(DOMAIN, issue_id) is None

    await coordinator.async_refresh()

    assert issue_registry.async_get_issue(DOMAIN, issue_id) is not None


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
    mock_statistics_anchor: AsyncMock,
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


async def test_async_set_alert_settings_success_applies_in_memory(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    mock_statistics_anchor: AsyncMock,
) -> None:
    """The validated copy is only assigned in memory once the API confirms it."""
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)
    await coordinator.async_refresh()
    assert coordinator.data.alert_settings.daily_notif_sms is False

    await coordinator.async_set_alert_settings(daily_notif_sms=True)
    await hass.async_block_till_done()

    assert coordinator.data.alert_settings.daily_notif_sms is True

    # The coordinator was created outside of the normal config entry setup
    # lifecycle, so nothing will cancel its debounced-refresh timer for us.
    await coordinator.async_shutdown()


async def test_async_set_alert_settings_serializes_concurrent_calls(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    mock_statistics_anchor: AsyncMock,
) -> None:
    """Concurrent pushes are serialized instead of overwriting each other.

    The client POSTs the full settings payload on every push. Without the
    lock, two concurrent calls would both read the same starting state and
    the second (last writer) would push a payload missing the first call's
    change. With the lock, the second call waits for the first to finish and
    re-reads the state it just applied, so both changes end up applied
    cumulatively.
    """
    mock_veolia_api.account_data.alert_settings = build_alert_settings(
        daily_notif_email=False, monthly_notif_email=False
    )
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)
    await coordinator.async_refresh()
    assert coordinator.data.alert_settings.daily_notif_email is False
    assert coordinator.data.alert_settings.monthly_notif_email is False

    release_first = asyncio.Event()

    async def delayed_push(_settings: AlertSettings) -> bool:
        # Holds whichever call is currently inside the lock open, so the
        # second call has time to queue up behind it before either one
        # completes.
        await release_first.wait()
        return True

    mock_veolia_api.set_alerts_settings.side_effect = delayed_push

    gather_task = asyncio.gather(
        coordinator.async_set_alert_settings(daily_notif_email=True),
        coordinator.async_set_alert_settings(monthly_notif_email=True),
    )
    # Let both tasks start: the first acquires the lock and blocks inside
    # the push, the second blocks waiting for the lock.
    await asyncio.sleep(0)
    release_first.set()
    await gather_task
    await hass.async_block_till_done()

    assert mock_veolia_api.set_alerts_settings.await_count == 2
    second_pushed_settings = mock_veolia_api.set_alerts_settings.call_args_list[1].args[
        0
    ]
    assert second_pushed_settings.daily_notif_email is True
    assert second_pushed_settings.monthly_notif_email is True

    assert coordinator.data.alert_settings.daily_notif_email is True
    assert coordinator.data.alert_settings.monthly_notif_email is True

    # The coordinator was created outside of the normal config entry setup
    # lifecycle, so nothing will cancel its debounced-refresh timer for us.
    await coordinator.async_shutdown()


async def test_async_set_alert_settings_rejected_raises(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    mock_statistics_anchor: AsyncMock,
) -> None:
    """A rejected settings update (API returns False) raises HomeAssistantError."""
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)
    await coordinator.async_refresh()
    mock_veolia_api.set_alerts_settings.return_value = False

    with pytest.raises(HomeAssistantError):
        await coordinator.async_set_alert_settings(daily_enabled=False)

    # The rejected change must not stick in memory: the UI keeps showing the
    # last value actually applied on the Veolia side.
    assert coordinator.data.alert_settings.daily_enabled is True


async def test_async_set_alert_settings_api_error_raises(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    mock_statistics_anchor: AsyncMock,
) -> None:
    """A VeoliaAPIError while pushing settings raises HomeAssistantError."""
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)
    await coordinator.async_refresh()
    mock_veolia_api.set_alerts_settings.side_effect = VeoliaAPIError("rejected")

    with pytest.raises(HomeAssistantError):
        await coordinator.async_set_alert_settings(daily_enabled=False)

    # The failed change must not stick in memory: the UI keeps showing the
    # last value actually applied on the Veolia side.
    assert coordinator.data.alert_settings.daily_enabled is True


async def test_async_set_alert_settings_unavailable_raises(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    mock_statistics_anchor: AsyncMock,
) -> None:
    """Alert settings unavailable (None) raises HomeAssistantError."""
    mock_veolia_api.account_data.alert_settings = None
    mock_config_entry.add_to_hass(hass)
    coordinator = VeoliaDataUpdateCoordinator(hass, mock_config_entry)
    await coordinator.async_refresh()

    with pytest.raises(HomeAssistantError):
        await coordinator.async_set_alert_settings(daily_enabled=True)

    mock_veolia_api.set_alerts_settings.assert_not_called()
