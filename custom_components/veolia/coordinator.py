"""DataUpdateCoordinator for integration_blueprint."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from dateutil.relativedelta import relativedelta

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import CONF_PORTAL_URL, DOMAIN, LOGGER
from .data import VeoliaConfigEntry
from .model import VeoliaModel
from .veolia_api import VeoliaAPI
from .veolia_api.exceptions import VeoliaAPIError, VeoliaAPIInvalidCredentialsError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class VeoliaDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: VeoliaConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=6),
        )
        LOGGER.debug("Initializing client VeoliaAPI")

        self.client_api = VeoliaAPI(
            username=self.config_entry.data[CONF_USERNAME],
            password=self.config_entry.data[CONF_PASSWORD],
            session=async_get_clientsession(hass),
            portal_url=self.config_entry.data.get(CONF_PORTAL_URL),
        )

        self._initial_historical_fetch = False

    async def _async_update_data(self) -> VeoliaModel:
        """Fetch and calculate data."""
        now = datetime.now()

        if not self._initial_historical_fetch:
            # First init
            LOGGER.debug("Initial fetch 1 year")
            end_date = date(now.year, now.month, 1)
            start_date = date(end_date.year - 1, end_date.month, 1)
        else:
            # Regular fetch
            LOGGER.debug("Periodic fetch - 2 months")
            start_date = date(now.year, now.month, 1) - relativedelta(months=1)
            end_date = date(now.year, now.month, 1)

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
        account_data = self.client_api.account_data
        today = dt_util.now().date()
        return VeoliaModel.from_account_data(account_data, today=today)
