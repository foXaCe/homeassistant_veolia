"""Config flow for the Veolia integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import aiohttp
from veolia_api import VeoliaAPI
from veolia_api.exceptions import VeoliaAPIInvalidCredentialsError
from veolia_api.portals import VEOLIA_PORTAL_CLIENTS
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    COMMUNE_TYPE_DIRECT,
    COMMUNE_TYPE_NOT_SERVED,
    COMMUNE_TYPE_REDIRECTED,
    COMMUNES_LOOKUP_URL,
    CONF_COMMUNE,
    CONF_COST_PER_M3,
    CONF_PORTAL_URL,
    CONF_POSTAL_CODE,
    DEFAULT_COST_PER_M3,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DOMAIN,
    LOGGER,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_POSTAL_CODE): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT)
        ),
    }
)

STEP_CREDENTIALS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD, autocomplete="current-password"
            )
        ),
    }
)

STEP_REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD, autocomplete="current-password"
            )
        ),
    }
)


class VeoliaFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for veolia."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize."""
        self._postal_code: str | None = None
        self._communes: list[dict[str, Any]] = []
        self._portal_url: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> VeoliaOptionsFlowHandler:
        """Create the options flow handler."""
        return VeoliaOptionsFlowHandler()

    async def _async_fetch_communes(self, postal_code: str) -> list[dict[str, Any]]:
        """Look up the communes served for a postal code."""
        session = async_get_clientsession(self.hass)
        async with session.get(
            COMMUNES_LOOKUP_URL,
            params={"q": postal_code},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            payload = await response.json()
        if not isinstance(payload, list):
            LOGGER.debug("Unexpected communes payload type: %s", type(payload).__name__)
            return []
        communes = [item for item in payload if isinstance(item, dict)]
        LOGGER.debug("Found %d commune(s) for the given postal code", len(communes))
        return communes

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

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the postal code and check portal eligibility."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._postal_code = user_input[CONF_POSTAL_CODE]
            try:
                self._communes = await self._async_fetch_communes(self._postal_code)
            except (aiohttp.ClientError, TimeoutError):
                LOGGER.debug("Commune lookup failed", exc_info=True)
                errors["base"] = "cannot_connect"
            else:
                if self._communes:
                    return await self.async_step_select_commune()
                errors["base"] = "no_communes_found"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_select_commune(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the selection of a commune."""
        errors: dict[str, str] = {}
        unsupported_hint = ""
        if user_input is not None:
            selected = next(
                (
                    commune
                    for commune in self._communes
                    if commune.get("libelle") == user_input[CONF_COMMUNE]
                ),
                None,
            )
            commune_type = selected.get("type_commune") if selected else None
            if commune_type == COMMUNE_TYPE_DIRECT:
                self._portal_url = None
                return await self.async_step_credentials()
            if commune_type == COMMUNE_TYPE_REDIRECTED:
                url_redirection = (
                    selected.get("url_redirection", "") if selected else ""
                )
                hostname = urlparse(url_redirection).hostname or ""
                if hostname in VEOLIA_PORTAL_CLIENTS:
                    self._portal_url = hostname
                    return await self.async_step_credentials()
                unsupported_hint = hostname
                errors["base"] = "commune_not_supported"
            elif commune_type == COMMUNE_TYPE_NOT_SERVED:
                errors["base"] = "commune_not_veolia"
            else:
                errors["base"] = "commune_not_supported"

        options = [
            commune["libelle"] for commune in self._communes if commune.get("libelle")
        ]
        return self.async_show_form(
            step_id="select_commune",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COMMUNE): SelectSelector(
                        SelectSelectorConfig(
                            options=options, mode=SelectSelectorMode.DROPDOWN
                        )
                    ),
                }
            ),
            errors=errors,
            description_placeholders={"unsupported_portal": unsupported_hint},
        )

    async def async_step_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for and validate the Veolia credentials."""
        errors: dict[str, str] = {}
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
            errors["base"] = error

        return self.async_show_form(
            step_id="credentials",
            data_schema=STEP_CREDENTIALS_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow updating the credentials of an existing entry."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            account_id, error = await self._async_validate(
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                entry.data.get(CONF_PORTAL_URL),
            )
            if error is None:
                await self.async_set_unique_id(account_id)
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_CREDENTIALS_SCHEMA,
                {CONF_USERNAME: entry.data[CONF_USERNAME]},
            ),
            errors=errors,
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
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        if user_input is not None:
            account_id, error = await self._async_validate(
                reauth_entry.data[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                reauth_entry.data.get(CONF_PORTAL_URL),
            )
            if error is None:
                await self.async_set_unique_id(account_id)
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_SCHEMA,
            errors=errors,
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
                data={
                    CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                    CONF_COST_PER_M3: float(user_input[CONF_COST_PER_M3]),
                }
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
                    vol.Required(
                        CONF_COST_PER_M3,
                        default=self.config_entry.options.get(
                            CONF_COST_PER_M3, DEFAULT_COST_PER_M3
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=0,
                            max=50,
                            step=0.01,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="€/m³",
                        )
                    ),
                }
            ),
        )
