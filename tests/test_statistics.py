"""Tests for the recorder external-statistics import helpers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.veolia.const import DOMAIN
from custom_components.veolia.statistics import build_statistic_id
from homeassistant.components.recorder import Recorder
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import VolumeConverter

from .const import MOCK_ACCOUNT_ID

DAILY_STATISTIC_ID = build_statistic_id(MOCK_ACCOUNT_ID, "daily_consumption")
MONTHLY_STATISTIC_ID = build_statistic_id(MOCK_ACCOUNT_ID, "monthly_consumption")


def _no_anchor(
    _hass: HomeAssistant, _n: int, _statistic_id: str, _convert_units: bool, _types: Any
) -> dict[str, Any]:
    """Return an empty result: no statistic has been imported yet."""
    return {}


def _anchor_at(
    statistic_id: str, anchor_date: date, anchor_sum: float, anchor_state: float
) -> Callable[..., Any]:
    """Build a get_last_statistics stand-in anchored on ``statistic_id`` only."""
    epoch = dt_util.start_of_local_day(anchor_date).timestamp()

    def _side_effect(
        _hass: HomeAssistant,
        _n: int,
        queried_id: str,
        _convert_units: bool,
        _types: Any,
    ) -> dict[str, Any]:
        if queried_id != statistic_id:
            return {}
        return {
            queried_id: [{"start": epoch, "sum": anchor_sum, "state": anchor_state}]
        }

    return _side_effect


async def test_import_volume_statistics_full_metadata(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The daily-consumption import call receives complete recorder metadata."""
    freezer.move_to("2026-07-08 12:00:00")
    mock_config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.veolia.statistics.get_last_statistics",
            side_effect=_no_anchor,
        ),
        patch(
            "custom_components.veolia.statistics.async_add_external_statistics"
        ) as mock_import,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    call = next(
        c
        for c in mock_import.call_args_list
        if c.args[1]["statistic_id"] == DAILY_STATISTIC_ID
    )
    metadata = call.args[1]
    assert metadata == {
        "mean_type": StatisticMeanType.NONE,
        "has_sum": True,
        "name": f"Veolia consommation journalière {MOCK_ACCOUNT_ID}",
        "source": DOMAIN,
        "statistic_id": DAILY_STATISTIC_ID,
        "unit_class": VolumeConverter.UNIT_CLASS,
        "unit_of_measurement": UnitOfVolume.LITERS,
    }


async def test_first_import_cumulates_from_zero_with_local_midnight_starts(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """With no prior statistic, sums accumulate from 0 at local midnight starts."""
    freezer.move_to("2026-07-08 12:00:00")
    mock_config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.veolia.statistics.get_last_statistics",
            side_effect=_no_anchor,
        ),
        patch(
            "custom_components.veolia.statistics.async_add_external_statistics"
        ) as mock_import,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    call = next(
        c
        for c in mock_import.call_args_list
        if c.args[1]["statistic_id"] == DAILY_STATISTIC_ID
    )
    stats = call.args[2]
    # Fixture daily data: 2026-07-01 (100L), 2026-07-03 (110L), 2026-07-08 (120L).
    assert [row["start"] for row in stats] == [
        dt_util.start_of_local_day(date(2026, 7, 1)),
        dt_util.start_of_local_day(date(2026, 7, 3)),
        dt_util.start_of_local_day(date(2026, 7, 8)),
    ]
    assert [row["sum"] for row in stats] == [100, 210, 330]


async def test_continuity_rewinds_and_reimports_last_row(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The anchored row is re-imported with its current value; older rows are not.

    Anchor: 2026-07-05, sum 4200.0, state 200.0. The rewind re-imports the
    07-05 row with its current API value (130 L) and a sum rebuilt from
    before that row (4200 - 200 + 130), then later days cumulate on top.
    """
    freezer.move_to("2026-07-08 12:00:00")
    mock_veolia_api.account_data.daily_consumption = [
        {"date_releve": "2026-07-03", "consommation": {"litre": 110}},
        {"date_releve": "2026-07-05", "consommation": {"litre": 130}},
        {"date_releve": "2026-07-08", "consommation": {"litre": 120}},
    ]
    mock_config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.veolia.statistics.get_last_statistics",
            side_effect=_anchor_at(DAILY_STATISTIC_ID, date(2026, 7, 5), 4200.0, 200.0),
        ),
        patch(
            "custom_components.veolia.statistics.async_add_external_statistics"
        ) as mock_import,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    call = next(
        c
        for c in mock_import.call_args_list
        if c.args[1]["statistic_id"] == DAILY_STATISTIC_ID
    )
    stats = call.args[2]
    # 2026-07-03 is strictly before the rewound cutoff (2026-07-04): immutable.
    assert [row["start"] for row in stats] == [
        dt_util.start_of_local_day(date(2026, 7, 5)),
        dt_util.start_of_local_day(date(2026, 7, 8)),
    ]
    assert stats[0]["state"] == 130
    assert stats[0]["sum"] == 4200.0 - 200.0 + 130
    assert stats[1]["sum"] == stats[0]["sum"] + 120


async def test_sum_does_not_regress_when_anchor_day_vanishes(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A vanished anchor day falls back to strict anchoring instead of regressing.

    Anchor: 2026-07-03, sum 450.0 (100 + 150 + 200), state 200.0 — as if a
    prior import already summed 07-01, 07-02 and 07-03. The portal's next
    fetch no longer returns 07-03 (a provisional day dropped or shifted)
    but does return a new 07-04 row. Rewinding onto the vanished 07-03 row
    would restart the running sum from 450 - 200 = 250 and re-derive it
    from only the 07-04 row (250 + 120 = 370 < 450): a silent regression
    that drops the already-counted 200 L. The guard must instead fall back
    to strict anchoring (initial_sum = 450, after = 07-03), so the 07-04
    row imports at 450 + 120 = 570 and no imported row is below 450.
    """
    freezer.move_to("2026-07-08 12:00:00")
    mock_veolia_api.account_data.daily_consumption = [
        {"date_releve": "2026-07-04", "consommation": {"litre": 120}},
    ]
    mock_config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.veolia.statistics.get_last_statistics",
            side_effect=_anchor_at(DAILY_STATISTIC_ID, date(2026, 7, 3), 450.0, 200.0),
        ),
        patch(
            "custom_components.veolia.statistics.async_add_external_statistics"
        ) as mock_import,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    call = next(
        c
        for c in mock_import.call_args_list
        if c.args[1]["statistic_id"] == DAILY_STATISTIC_ID
    )
    stats = call.args[2]
    assert [row["start"] for row in stats] == [
        dt_util.start_of_local_day(date(2026, 7, 4))
    ]
    assert stats[0]["sum"] == 570.0
    assert all(row["sum"] >= 450.0 for row in stats)


async def test_current_month_value_updates_on_reimport(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The in-progress month converges to its latest API value, without double count.

    A previous refresh imported July at 1.0 m³ (anchor: 2026-07-01,
    sum 4.2, state 1.0). The API now reports July at 2.5 m³: the July row
    is re-imported with state 2.5 and sum 4.2 - 1.0 + 2.5.
    """
    freezer.move_to("2026-07-08 12:00:00")
    mock_veolia_api.account_data.monthly_consumption = [
        {"annee": 2026, "mois": 6, "consommation": {"m3": 3.2}},
        {"annee": 2026, "mois": 7, "consommation": {"m3": 2.5}},
    ]
    mock_config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.veolia.statistics.get_last_statistics",
            side_effect=_anchor_at(MONTHLY_STATISTIC_ID, date(2026, 7, 1), 4.2, 1.0),
        ),
        patch(
            "custom_components.veolia.statistics.async_add_external_statistics"
        ) as mock_import,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    call = next(
        c
        for c in mock_import.call_args_list
        if c.args[1]["statistic_id"] == MONTHLY_STATISTIC_ID
    )
    stats = call.args[2]
    # June (2026-06-01) is before the rewound cutoff (2026-06-30): immutable.
    assert [row["start"] for row in stats] == [
        dt_util.start_of_local_day(date(2026, 7, 1))
    ]
    assert stats[0]["state"] == 2.5
    assert stats[0]["sum"] == pytest.approx(4.2 - 1.0 + 2.5)


async def test_dst_transition_keeps_local_midnight_starts(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Rows spanning the CET→CEST spring-forward keep true local midnights.

    2026-03-29 is the EU spring-forward day: every row must start at
    00:00 local time, so the UTC gap between the 29th and the 30th is
    only 23 hours and the UTC offset changes from +01:00 to +02:00.
    """
    await hass.config.async_set_time_zone("Europe/Paris")
    freezer.move_to("2026-04-01 12:00:00")
    mock_veolia_api.account_data.daily_consumption = [
        {"date_releve": "2026-03-28", "consommation": {"litre": 100}},
        {"date_releve": "2026-03-29", "consommation": {"litre": 110}},
        {"date_releve": "2026-03-30", "consommation": {"litre": 120}},
    ]
    mock_config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.veolia.statistics.get_last_statistics",
            side_effect=_no_anchor,
        ),
        patch(
            "custom_components.veolia.statistics.async_add_external_statistics"
        ) as mock_import,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    call = next(
        c
        for c in mock_import.call_args_list
        if c.args[1]["statistic_id"] == DAILY_STATISTIC_ID
    )
    starts = [row["start"] for row in call.args[2]]
    assert all(start.tzinfo is not None for start in starts)
    assert [dt_util.as_local(start).hour for start in starts] == [0, 0, 0]
    # Same-tzinfo subtraction is wall-clock arithmetic; convert to UTC to
    # measure the real elapsed time across the transition.
    utc_starts = [dt_util.as_utc(start) for start in starts]
    assert (utc_starts[1] - utc_starts[0]).total_seconds() == 24 * 3600
    assert (utc_starts[2] - utc_starts[1]).total_seconds() == 23 * 3600
    assert starts[0].utcoffset() != starts[2].utcoffset()


async def test_no_op_when_no_data_on_or_after_rewound_anchor(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """No import happens when the API returns nothing on/after the rewound row.

    With the rewind, the last imported row is re-imported whenever the API
    still returns it; a true no-op only remains when the API has no data
    dated on or after the rewound cutoff.
    """
    freezer.move_to("2026-07-08 12:00:00")
    # The API no longer returns anything past 2026-07-03, while the last
    # imported statistic is dated 2026-07-08 (rewound cutoff: 2026-07-07).
    mock_veolia_api.account_data.daily_consumption = [
        {"date_releve": "2026-07-01", "consommation": {"litre": 100}},
        {"date_releve": "2026-07-03", "consommation": {"litre": 110}},
    ]
    mock_config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.veolia.statistics.get_last_statistics",
            side_effect=_anchor_at(DAILY_STATISTIC_ID, date(2026, 7, 8), 330.0, 120.0),
        ),
        patch(
            "custom_components.veolia.statistics.async_add_external_statistics"
        ) as mock_import,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert all(
        c.args[1]["statistic_id"] != DAILY_STATISTIC_ID
        for c in mock_import.call_args_list
    )
