"""DataUpdateCoordinator for the Veolia integration."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from dateutil.relativedelta import relativedelta

from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import CONF_PORTAL_URL, DEFAULT_SCAN_INTERVAL_HOURS, DOMAIN, LOGGER
from .model import VeoliaModel
from .veolia_api import VeoliaAPI
from .veolia_api.exceptions import VeoliaAPIError, VeoliaAPIInvalidCredentialsError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import VeoliaConfigEntry


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
        self._initial_historical_fetch = False

    async def _async_update_data(self) -> VeoliaModel:
        """Fetch consumption data and compute the exposed model."""
        today = dt_util.now().date()
        end_date = date(today.year, today.month, 1)
        if not self._initial_historical_fetch:
            LOGGER.debug("Initial fetch: one year of history")
            start_date = date(end_date.year - 1, end_date.month, 1)
        else:
            LOGGER.debug("Periodic fetch: two months of history")
            start_date = end_date - relativedelta(months=1)

        try:
            await self.client_api.fetch_all_data(start_date, end_date)
        except VeoliaAPIInvalidCredentialsError as exception:
            # Bad credentials → trigger the reauthentication flow.
            raise ConfigEntryAuthFailed(exception) from exception
        except VeoliaAPIError as exception:
            # Transient error (network, rate limit, API down) → retry next cycle.
            raise UpdateFailed(exception) from exception

        # Mark the initial historical fetch done only after it succeeded.
        self._initial_historical_fetch = True
        return VeoliaModel.from_account_data(self.client_api.account_data, today=today)

    async def async_set_alert_settings(self, **changes: bool | int) -> None:
        """Apply alert-settings changes and push them to the Veolia API.

        Mutates the in-memory settings first so the UI reflects the change
        immediately, pushes them to the API, then requests a refresh.

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
        for field, value in changes.items():
            setattr(settings, field, value)
        LOGGER.debug("Pushing alert settings changes: %s", changes)
        try:
            success = await self.client_api.set_alerts_settings(settings)
        except VeoliaAPIError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="set_alert_failed",
            ) from err
        if not success:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="set_alert_failed",
            )
        await self.async_request_refresh()
