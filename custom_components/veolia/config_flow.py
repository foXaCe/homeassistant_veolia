"""Config flow for veolia integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    COMMUNES_LOOKUP_URL,
    CONF_PORTAL_URL,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DOMAIN,
    LOGGER,
)
from .veolia_api import VeoliaAPI
from .veolia_api.exceptions import VeoliaAPIInvalidCredentialsError
from .veolia_api.portals import VEOLIA_PORTAL_CLIENTS


class VeoliaFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for veolia."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize."""
        self._errors = {}
        self._postal_code = None
        self._communes = []
        self._portal_url: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> VeoliaOptionsFlowHandler:
        """Create the options flow handler."""
        return VeoliaOptionsFlowHandler()

    async def _async_validate(
        self, username: str, password: str, portal_url: str | None
    ) -> tuple[str | None, str | None]:
        """Validate credentials.

        Returns ``(account_id, None)`` on success, ``(None, error_key)`` otherwise.
        """
        api = VeoliaAPI(
            username,
            password,
            async_get_clientsession(self.hass),
            portal_url=portal_url,
        )
        try:
            if await api.login():
                account_id = api.account_data.id_abonnement
                return (str(account_id) if account_id else username, None)
        except VeoliaAPIInvalidCredentialsError:
            return None, "invalid_credentials"
        except Exception:  # noqa: BLE001
            LOGGER.debug("Unknown exception during validation", exc_info=True)
            return None, "unknown"
        return None, "invalid_credentials"

    async def async_step_user(self, user_input=None) -> dict:
        """Handle a flow initialized by the user."""
        self._errors = {}

        if user_input is not None:
            self._postal_code = user_input["postal_code"]
            return await self.async_step_select_commune()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("postal_code"): str}),
            errors=self._errors,
        )

    async def async_step_select_commune(self, user_input=None) -> dict:
        """Handle the selection of a commune."""
        LOGGER.debug("Check city postal to for integration compatibility")
        if user_input is not None:
            selected_commune = next(
                (
                    commune
                    for commune in self._communes
                    if commune["libelle"] == user_input["commune"]
                ),
                None,
            )
            if selected_commune["type_commune"] == "NON_REDIRIGE":
                self._portal_url = None
                return await self.async_step_credentials()

            if selected_commune["type_commune"] == "REDIRIGE":
                url_redirection = selected_commune.get("url_redirection", "")
                hostname = urlparse(url_redirection).hostname or ""
                if hostname in VEOLIA_PORTAL_CLIENTS:
                    self._portal_url = hostname
                    return await self.async_step_credentials()
                self._errors["base"] = "commune_not_supported"
            elif selected_commune["type_commune"] == "NON_DESSERVIE":
                self._errors["base"] = "commune_not_veolia"
            else:
                self._errors["base"] = "commune_not_supported"

        LOGGER.debug("Fetching communes for postal code %s", self._postal_code)
        session = async_get_clientsession(self.hass)
        async with session.get(
            COMMUNES_LOOKUP_URL,
            params={"q": self._postal_code},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            self._communes = await response.json()
            LOGGER.debug("Communes found: %s", self._communes)

        if not self._communes:
            self._errors["base"] = "no_communes_found"

        commune_options = {
            commune["libelle"]: commune["libelle"] for commune in self._communes
        }

        return self.async_show_form(
            step_id="select_commune",
            data_schema=vol.Schema({vol.Required("commune"): vol.In(commune_options)}),
            errors=self._errors,
        )

    async def async_step_credentials(self, user_input=None) -> dict:
        """Handle the input of credentials."""
        LOGGER.debug("Request credentials")
        self._errors = {}
        if user_input is not None:
            account_id, error = await self._async_validate(
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                self._portal_url,
            )
            if error is None:
                await self.async_set_unique_id(account_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data={**user_input, CONF_PORTAL_URL: self._portal_url},
                )
            self._errors["base"] = error
            return await self._show_credentials_form(user_input)

        return await self._show_credentials_form(user_input)

    async def _show_credentials_form(self, user_input) -> dict:
        """Show the configuration form to input credentials."""
        return self.async_show_form(
            step_id="credentials",
            data_schema=vol.Schema(
                {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str},
            ),
            errors=self._errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when credentials become invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm re-authentication by asking for a new password."""
        self._errors = {}
        reauth_entry = self._get_reauth_entry()
        if user_input is not None:
            _, error = await self._async_validate(
                reauth_entry.data[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                reauth_entry.data.get(CONF_PORTAL_URL),
            )
            if error is None:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )
            self._errors["base"] = error

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=self._errors,
            description_placeholders={CONF_USERNAME: reauth_entry.data[CONF_USERNAME]},
        )


class VeoliaOptionsFlowHandler(OptionsFlowWithReload):
    """Handle the Veolia integration options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the integration options."""
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])}
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=1,
                            max=24,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="h",
                        )
                    ),
                }
            ),
        )
