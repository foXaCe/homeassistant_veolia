"""Recorder external-statistics import helpers for the Veolia integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.helpers.recorder import get_instance
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import VolumeConverter

from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from datetime import date

    from homeassistant.core import HomeAssistant

    from .model import StatisticsRow


class LastStat(NamedTuple):
    """Last imported statistics row of a series (anchor for the next import)."""

    sum: float
    state: float | None
    date: date


def build_statistic_id(account_id: str, key: str) -> str:
    """Return the external statistic id for this account and series."""
    return f"{DOMAIN}:{account_id}_{key}"


async def get_last_stat(hass: HomeAssistant, statistic_id: str) -> LastStat | None:
    """Return the last imported row (sum, state, local date) for ``statistic_id``.

    Returns None when no statistic has been imported yet for this id, which
    tells the caller to fall back to a full historical fetch. A missing
    ``sum`` on an existing row is treated as 0.0; a missing ``state`` is
    kept as None so the caller can fall back to strict (non-rewound)
    anchoring.
    """
    last_stat = await get_instance(hass).async_add_executor_job(
        get_last_statistics, hass, 1, statistic_id, True, {"state", "sum"}
    )
    if not last_stat or not last_stat.get(statistic_id):
        return None
    row = last_stat[statistic_id][0]
    return LastStat(
        sum=row.get("sum") or 0.0,
        state=row.get("state"),
        date=dt_util.as_local(dt_util.utc_from_timestamp(row["start"])).date(),
    )


def import_volume_statistics(
    hass: HomeAssistant,
    statistic_id: str,
    name: str,
    stats: list[StatisticsRow],
    unit: str,
    unit_class: str | None = VolumeConverter.UNIT_CLASS,
) -> None:
    """Convert calendar-dated rows to StatisticData and push them to the recorder.

    ``stats`` rows are keyed by calendar ``date``; each is converted here to
    a tz-aware start of local day before import. No-op (with a debug log)
    when ``stats`` is empty. The cost series is not a volume, so it passes
    ``unit_class=None``, a monetary series with no unit class.
    """
    if not stats:
        LOGGER.debug("No statistics to import for %s", statistic_id)
        return
    metadata = StatisticMetaData(
        mean_type=StatisticMeanType.NONE,
        has_sum=True,
        name=name,
        source=DOMAIN,
        statistic_id=statistic_id,
        unit_class=unit_class,
        unit_of_measurement=unit,
    )
    statistic_data: list[StatisticData] = [
        StatisticData(
            start=dt_util.start_of_local_day(row["date"]),
            state=row["state"],
            sum=row["sum"],
        )
        for row in stats
    ]
    LOGGER.debug("Importing %d statistics rows for %s", len(stats), statistic_id)
    async_add_external_statistics(hass, metadata, statistic_data)
