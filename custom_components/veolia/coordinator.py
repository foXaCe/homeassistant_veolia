"""DataUpdateCoordinator for the Veolia integration."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from typing import TYPE_CHECKING

import aiohttp
from veolia_api import VeoliaAPI
from veolia_api.exceptions import VeoliaAPIError, VeoliaAPIInvalidCredentialsError

from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    UnitOfVolume,
)
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_PORTAL_URL,
    CONSECUTIVE_FAILURES_FOR_ISSUE,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DOMAIN,
    LOGGER,
    STATISTIC_NAME_DAILY,
    STATISTIC_NAME_INDEX,
    STATISTIC_NAME_MONTHLY,
)
from .model import (
    VeoliaModel,
    _compute_daily_stats,
    _compute_index_stats,
    _compute_monthly_stats,
    _monthly_record_date,
    _record_dates,
)
from .statistics import (
    LastStat,
    build_statistic_id,
    get_last_stat,
    import_volume_statistics,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import VeoliaConfigEntry


def _anchored_series_params(
    anchor: LastStat | None,
    fetched_dates: set[date],
) -> tuple[float, date | None]:
    """Return the (initial_sum, after) builder parameters for an anchored series.

    Implements the one-row rewind: the ``after`` cutoff is moved one day
    before the last imported row, and the running sum restarts from before
    that row (``sum - state``). The last imported row is thus re-imported
    with its current API value — the recorder upserts rows sharing the
    same ``start`` — so a partial value (in-progress month, provisional
    last day) converges to its final value on later refreshes, while every
    older row stays immutable.

    The rewind only happens when the anchor row is present in the fresh
    fetch (``anchor.date in fetched_dates``): rewinding onto a vanished
    row would subtract its contribution from the running sum without ever
    re-adding it, making the recorder ``sum`` regress. When the anchor row
    is missing — or has no stored ``state`` — fall back to strict
    anchoring (last row immutable, sum continues from ``anchor.sum``).
    Without an anchor the series is imported from scratch.
    """
    if anchor is None:
        return 0.0, None
    if anchor.state is None or anchor.date not in fetched_dates:
        return anchor.sum, anchor.date
    return anchor.sum - anchor.state, anchor.date - timedelta(days=1)


class VeoliaDataUpdateCoordinator(DataUpdateCoordinator[VeoliaModel]):
    """Coordinator fetching and computing Veolia account data."""

    config_entry: VeoliaConfigEntry

    def __init__(self, hass: HomeAssistant, entry: VeoliaConfigEntry) -> None:
        """Initialize the coordinator and its API client."""
        scan_interval: int = entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS
        )
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(hours=scan_interval),
        )
        LOGGER.debug("Initializing client VeoliaAPI")
        self.client_api = VeoliaAPI(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            session=async_get_clientsession(hass),
            portal_url=entry.data.get(CONF_PORTAL_URL),
        )
        self._consecutive_failures = 0

    async def _async_update_data(self) -> VeoliaModel:
        """Fetch consumption data, compute the model and import statistics.

        The fetch window and the statistics ``sum`` are both anchored on
        the last statistic already imported for the daily-consumption
        series: with no prior statistic, a full year of history is fetched
        (initial setup); otherwise only the month containing the last
        imported day onward is re-fetched, since the client fetches whole
        months and that always covers everything missing, including after
        a long outage. Each series is imported with a one-row rewind of
        its anchor (see ``_anchored_series_params``): the most recently
        imported row is re-imported with its current API value, so the
        in-progress month and a provisional last day converge to their
        final values, while all older rows stay immutable.
        """
        today = dt_util.now().date()
        end_date = date(today.year, today.month, 1)
        account_id = str(self.config_entry.unique_id)
        daily_statistic_id = build_statistic_id(account_id, "daily_consumption")
        monthly_statistic_id = build_statistic_id(account_id, "monthly_consumption")
        index_statistic_id = build_statistic_id(account_id, "index")

        daily_anchor = await get_last_stat(self.hass, daily_statistic_id)
        monthly_anchor = await get_last_stat(self.hass, monthly_statistic_id)
        index_anchor = await get_last_stat(self.hass, index_statistic_id)

        if daily_anchor is None:
            start_date = date(end_date.year - 1, end_date.month, 1)
        else:
            start_date = daily_anchor.date.replace(day=1)
        LOGGER.debug("Fetching consumption data from %s to %s", start_date, end_date)

        try:
            await self.client_api.fetch_all_data(start_date, end_date)
        except VeoliaAPIInvalidCredentialsError as exception:
            # Bad credentials → trigger the reauthentication flow.
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from exception
        except VeoliaAPIError as exception:
            # Transient error (network, rate limit, API down) → retry next cycle.
            self._register_failure()
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(exception)},
            ) from exception
        except (aiohttp.ClientError, TimeoutError) as exception:
            # Network/transport error that escaped the client's retry layer.
            self._register_failure()
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(exception)},
            ) from exception

        self._register_success()

        account_data = self.client_api.account_data
        model = VeoliaModel.from_account_data(account_data, today=today)

        daily = account_data.daily_consumption or []
        monthly = account_data.monthly_consumption or []

        daily_initial_sum, daily_after = _anchored_series_params(
            daily_anchor, fetched_dates=_record_dates(daily)
        )
        monthly_initial_sum, monthly_after = _anchored_series_params(
            monthly_anchor,
            fetched_dates=_record_dates(monthly, _monthly_record_date),
        )
        # The index series carries absolute values (sum == state), so only
        # the rewound cutoff matters: re-importing its last row is safe.
        index_after = index_anchor.date - timedelta(days=1) if index_anchor else None

        import_volume_statistics(
            self.hass,
            daily_statistic_id,
            STATISTIC_NAME_DAILY.format(account_id=account_id),
            _compute_daily_stats(
                daily, initial_sum=daily_initial_sum, after=daily_after
            ),
            UnitOfVolume.LITERS,
        )
        import_volume_statistics(
            self.hass,
            monthly_statistic_id,
            STATISTIC_NAME_MONTHLY.format(account_id=account_id),
            _compute_monthly_stats(
                monthly, initial_sum=monthly_initial_sum, after=monthly_after
            ),
            UnitOfVolume.CUBIC_METERS,
        )
        import_volume_statistics(
            self.hass,
            index_statistic_id,
            STATISTIC_NAME_INDEX.format(account_id=account_id),
            _compute_index_stats(daily, after=index_after),
            UnitOfVolume.CUBIC_METERS,
        )

        return model

    def _register_failure(self) -> None:
        """Track a failed refresh and raise a repair issue past the threshold.

        The issue is created exactly once (``==``, not ``>=``) once the
        streak reaches ``CONSECUTIVE_FAILURES_FOR_ISSUE`` consecutive
        failures, so a long outage surfaces a single actionable repair issue
        instead of flapping on every subsequent failed cycle.
        """
        self._consecutive_failures += 1
        if self._consecutive_failures == CONSECUTIVE_FAILURES_FOR_ISSUE:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                f"api_down_{self.config_entry.entry_id}",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="api_down",
            )

    def _register_success(self) -> None:
        """Reset the failure streak and clear any ``api_down`` repair issue."""
        self._consecutive_failures = 0
        ir.async_delete_issue(
            self.hass, DOMAIN, f"api_down_{self.config_entry.entry_id}"
        )

    async def async_set_alert_settings(self, **changes: bool | int) -> None:
        """Apply alert-settings changes and push them to the Veolia API.

        Pushes a copy of the settings with the requested changes applied
        first; the in-memory settings are only updated once the API confirms
        the push succeeded, so a rejected or failed update leaves the UI
        showing the last value actually applied on the Veolia side.

        Raises:
            HomeAssistantError: if the settings are unavailable or the API
                rejects the update.

        """
        settings = self.data.alert_settings
        if settings is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="alert_settings_unavailable",
            )
        updated = replace(settings, **changes)
        LOGGER.debug("Pushing alert settings changes: %s", changes)
        try:
            success = await self.client_api.set_alerts_settings(updated)
        except (VeoliaAPIError, aiohttp.ClientError, TimeoutError) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="set_alert_failed",
            ) from err
        if not success:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="set_alert_failed",
            )
        self.data.raw.alert_settings = updated
        await self.async_request_refresh()
