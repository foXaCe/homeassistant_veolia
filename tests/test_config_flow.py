"""Tests for the Veolia config flow."""

from __future__ import annotations

from unittest.mock import MagicMock

import aiohttp
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from veolia_api.exceptions import VeoliaAPIInvalidCredentialsError

from custom_components.veolia.const import COMMUNES_LOOKUP_URL, CONF_PORTAL_URL, DOMAIN
from homeassistant import config_entries
from homeassistant.components.recorder import Recorder
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .const import (
    COMMUNE_DIRECT,
    COMMUNE_NOT_SERVED,
    COMMUNE_REDIRECTED_SUPPORTED,
    COMMUNE_REDIRECTED_UNSUPPORTED,
    MOCK_ACCOUNT_ID,
    MOCK_CONFIG_ENTRY_DATA,
    MOCK_PASSWORD,
    MOCK_POSTAL_CODE,
    MOCK_USERNAME,
)


def _mock_communes(aioclient_mock: AiohttpClientMocker, *communes: dict) -> None:
    """Register the communes lookup response."""
    aioclient_mock.get(COMMUNES_LOOKUP_URL, json=list(communes))


async def _start_to_select_commune(hass: HomeAssistant) -> dict:
    """Start the user flow and submit the postal code."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"postal_code": MOCK_POSTAL_CODE}
    )


# --------------------------------------------------------------------------
# Nominal flows
# --------------------------------------------------------------------------


async def test_full_flow_non_redirige(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    aioclient_mock: AiohttpClientMocker,
    mock_veolia_api: MagicMock,
) -> None:
    """A direct (NON_REDIRIGE) commune completes with no portal_url set."""
    _mock_communes(aioclient_mock, COMMUNE_DIRECT)
    result = await _start_to_select_commune(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_commune"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"commune": COMMUNE_DIRECT["libelle"]}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "credentials"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_USERNAME
    assert result["data"][CONF_USERNAME] == MOCK_USERNAME
    assert result["data"][CONF_PORTAL_URL] is None

    entry = hass.config_entries.async_entry_for_domain_unique_id(
        DOMAIN, MOCK_ACCOUNT_ID
    )
    assert entry is not None
    assert entry.state is config_entries.ConfigEntryState.LOADED


async def test_full_flow_redirige_supported_portal(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    aioclient_mock: AiohttpClientMocker,
    mock_veolia_api: MagicMock,
) -> None:
    """A REDIRIGE commune to a supported portal sets the portal_url."""
    _mock_communes(aioclient_mock, COMMUNE_REDIRECTED_SUPPORTED)
    result = await _start_to_select_commune(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"commune": COMMUNE_REDIRECTED_SUPPORTED["libelle"]}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "credentials"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PORTAL_URL] == "www.ea-pm.fr"


async def test_flow_redirige_unsupported_portal(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A REDIRIGE commune to an unsupported portal shows an error."""
    _mock_communes(aioclient_mock, COMMUNE_REDIRECTED_UNSUPPORTED)
    result = await _start_to_select_commune(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"commune": COMMUNE_REDIRECTED_UNSUPPORTED["libelle"]}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_commune"
    assert result["errors"] == {"base": "commune_not_supported"}


async def test_flow_commune_not_served(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A NON_DESSERVIE commune shows the commune_not_veolia error."""
    _mock_communes(aioclient_mock, COMMUNE_NOT_SERVED)
    result = await _start_to_select_commune(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"commune": COMMUNE_NOT_SERVED["libelle"]}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_commune"
    assert result["errors"] == {"base": "commune_not_veolia"}


async def test_flow_no_communes_found(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """An empty communes list shows the no_communes_found error."""
    _mock_communes(aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"postal_code": MOCK_POSTAL_CODE}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "no_communes_found"}


async def test_flow_unexpected_communes_payload(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A non-list communes payload shows no_communes_found instead of raising."""
    aioclient_mock.get(COMMUNES_LOOKUP_URL, json={"error": "oops"})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"postal_code": MOCK_POSTAL_CODE}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "no_communes_found"}


async def test_flow_cannot_connect(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A network error during the commune lookup shows cannot_connect."""
    aioclient_mock.get(COMMUNES_LOOKUP_URL, exc=aiohttp.ClientError())
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"postal_code": MOCK_POSTAL_CODE}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_flow_invalid_credentials(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    aioclient_mock: AiohttpClientMocker,
    mock_veolia_api: MagicMock,
) -> None:
    """Rejected credentials show the invalid_credentials error."""
    mock_veolia_api.login.side_effect = VeoliaAPIInvalidCredentialsError("nope")
    _mock_communes(aioclient_mock, COMMUNE_DIRECT)
    result = await _start_to_select_commune(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"commune": COMMUNE_DIRECT["libelle"]}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: "wrong"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "credentials"
    assert result["errors"] == {"base": "invalid_credentials"}


async def test_flow_login_returns_false_shows_invalid_credentials(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    aioclient_mock: AiohttpClientMocker,
    mock_veolia_api: MagicMock,
) -> None:
    """A login() call that returns False (no exception) is invalid_credentials."""
    mock_veolia_api.login.return_value = False
    _mock_communes(aioclient_mock, COMMUNE_DIRECT)
    result = await _start_to_select_commune(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"commune": COMMUNE_DIRECT["libelle"]}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "credentials"
    assert result["errors"] == {"base": "invalid_credentials"}


async def test_flow_commune_unknown_type_shows_commune_not_supported(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A commune with an unrecognized type_commune falls to the else branch."""
    weird_commune = {"libelle": "Commune Bizarre", "type_commune": "SOME_OTHER_TYPE"}
    _mock_communes(aioclient_mock, weird_commune)
    result = await _start_to_select_commune(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"commune": weird_commune["libelle"]}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_commune"
    assert result["errors"] == {"base": "commune_not_supported"}


async def test_flow_unknown_error(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    aioclient_mock: AiohttpClientMocker,
    mock_veolia_api: MagicMock,
) -> None:
    """An unexpected exception during validation shows the unknown error."""
    mock_veolia_api.login.side_effect = RuntimeError("boom")
    _mock_communes(aioclient_mock, COMMUNE_DIRECT)
    result = await _start_to_select_commune(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"commune": COMMUNE_DIRECT["libelle"]}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "credentials"
    assert result["errors"] == {"base": "unknown"}


async def test_flow_already_configured(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    aioclient_mock: AiohttpClientMocker,
    mock_veolia_api: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A second flow resolving to the same account id aborts."""
    mock_config_entry.add_to_hass(hass)
    _mock_communes(aioclient_mock, COMMUNE_DIRECT)
    result = await _start_to_select_commune(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"commune": COMMUNE_DIRECT["libelle"]}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# --------------------------------------------------------------------------
# Reauth
# --------------------------------------------------------------------------


async def test_reauth_flow_success(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_veolia_api: MagicMock,
) -> None:
    """A successful reauth updates the password and reloads the entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id=MOCK_ACCOUNT_ID,
        data={**MOCK_CONFIG_ENTRY_DATA, CONF_PASSWORD: "old-password"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "new-password"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "new-password"


async def test_reauth_flow_unique_id_mismatch(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_veolia_api: MagicMock,
) -> None:
    """A reauth resolving to a different account id aborts without changing the password."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="some-other-account-id",
        data={**MOCK_CONFIG_ENTRY_DATA, CONF_PASSWORD: "old-password"},
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "new-password"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"
    assert entry.data[CONF_PASSWORD] == "old-password"


async def test_reauth_flow_invalid_credentials(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_veolia_api: MagicMock,
) -> None:
    """A reauth attempt with still-wrong credentials shows an error."""
    mock_veolia_api.login.side_effect = VeoliaAPIInvalidCredentialsError("nope")
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id=MOCK_ACCOUNT_ID,
        data={**MOCK_CONFIG_ENTRY_DATA, CONF_PASSWORD: "old-password"},
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "still-wrong"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {"base": "invalid_credentials"}


# --------------------------------------------------------------------------
# Reconfigure
# --------------------------------------------------------------------------


async def test_reconfigure_flow_success(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_veolia_api: MagicMock,
) -> None:
    """A reconfigure flow updates credentials when the account id matches."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id=MOCK_ACCOUNT_ID,
        data={**MOCK_CONFIG_ENTRY_DATA, CONF_PASSWORD: "old-password"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: "new-password"},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_PASSWORD] == "new-password"


async def test_reconfigure_flow_invalid_credentials(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_veolia_api: MagicMock,
) -> None:
    """A reconfigure attempt with rejected credentials shows an error."""
    mock_veolia_api.login.side_effect = VeoliaAPIInvalidCredentialsError("nope")
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id=MOCK_ACCOUNT_ID,
        data={**MOCK_CONFIG_ENTRY_DATA, CONF_PASSWORD: "old-password"},
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: "still-wrong"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["errors"] == {"base": "invalid_credentials"}


async def test_reconfigure_flow_unique_id_mismatch(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_veolia_api: MagicMock,
) -> None:
    """A reconfigure resolving to a different account id aborts."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="some-other-account-id",
        data={**MOCK_CONFIG_ENTRY_DATA, CONF_PASSWORD: "old-password"},
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"
