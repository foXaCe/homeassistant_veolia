"""Recorder statistics import helpers for the Veolia integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.util.unit_conversion import VolumeConverter

from .const import LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .model import StatisticsRow


def import_volume_statistics(
    hass: HomeAssistant,
    statistic_id: str,
    stats: list[StatisticsRow],
    unit: str,
) -> None:
    """Import cumulative volume statistics rows for an entity.

    ``stats`` rows follow the recorder format: ``start`` (tz-aware datetime),
    ``state`` and ``sum``.
    """
    if not stats:
        LOGGER.debug("No statistics to import for %s", statistic_id)
        return
    metadata = StatisticMetaData(
        mean_type=StatisticMeanType.NONE,
        has_sum=True,
        name=None,
        source="recorder",
        statistic_id=statistic_id,
        unit_class=VolumeConverter.UNIT_CLASS,
        unit_of_measurement=unit,
    )
    LOGGER.debug("Importing %d statistics rows for %s", len(stats), statistic_id)
    async_import_statistics(hass, metadata, cast("list[StatisticData]", stats))
