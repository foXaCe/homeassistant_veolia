"""Tests for the vendored VeoliaAPI client."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)
import tenacity

from custom_components.veolia.veolia_api import VeoliaAPI
from custom_components.veolia.veolia_api.constants import LOGIN_URL, TYPE_FRONT
from custom_components.veolia.veolia_api.exceptions import (
    VeoliaAPIGetDataError,
    VeoliaAPIInvalidCredentialsError,
    VeoliaAPISetDataError,
    VeoliaAPITokenError,
)
from custom_components.veolia.veolia_api.model import AlertSettings
from custom_components.veolia.veolia_api.portals import DEFAULT_BACKEND_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

USERNAME = "test@example.com"
PASSWORD = "secret"  # noqa: S105
ACCOUNT_ID = "1235075"
NUMERO_PDS = "001OVAH"

ESPACE_CLIENT_URL = f"{DEFAULT_BACKEND_URL}/espace-client?type-front={TYPE_FRONT}"
FACTURATION_URL = f"{DEFAULT_BACKEND_URL}/abonnements/{ACCOUNT_ID}/facturation"
ALERTES_URL = f"{DEFAULT_BACKEND_URL}/alertes/{NUMERO_PDS}"
MENSUALISATION_URL = (
    f"{DEFAULT_BACKEND_URL}/abonnements/{ACCOUNT_ID}/facturation/mensualisation/plan"
)
MENSUELLES_URL = f"{DEFAULT_BACKEND_URL}/consommations/{ACCOUNT_ID}/mensuelles"
JOURNALIERES_URL = f"{DEFAULT_BACKEND_URL}/consommations/{ACCOUNT_ID}/journalieres"

ESPACE_CLIENT_PAYLOAD = {
    "contacts": [
        {
            "id_contact": "contact-99",
            "tiers": [
                {
                    "id": "tiers-99",
                    "abonnements": [
                        {
                            "id_abonnement": ACCOUNT_ID,
                            "numero_compteur": "U24BA285500",
                            "adresse_de_branchement": "1 rue de Test",
                            "emplacement_compteur": "Cave",
                            "libelle_contrat": "Contrat eau",
                            "statut": "ACTIF",
                        }
                    ],
                }
            ],
        }
    ]
}

FACTURATION_PAYLOAD = {
    "numero_pds": NUMERO_PDS,
    "solde": 12.5,
    "dernier_index_releve": 337.0,
    "date_index_releve": "2026-07-08",
    "mode_releve": "TELERELEVE",
    "mode_paiement": "PRELEVEMENT",
    "numero_client": "CLIENT-1",
    "titulaire": "M. Test",
    "marque": "ITRON",
    "date_debut_abonnement": "2018-08-01",
}


def _cognito_ok() -> dict:
    """Return a successful Cognito authentication payload."""
    return {"AuthenticationResult": {"AccessToken": "tok-123", "ExpiresIn": 3600}}


@pytest.fixture
def api(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> VeoliaAPI:
    """Return a VeoliaAPI client bound to the injected (mocked) HA session."""
    return VeoliaAPI(USERNAME, PASSWORD, session=async_get_clientsession(hass))


async def test_login_success(
    api: VeoliaAPI, aioclient_mock: AiohttpClientMocker
) -> None:
    """A full login populates the account data from Cognito + espace-client."""
    aioclient_mock.post(LOGIN_URL, json=_cognito_ok())
    aioclient_mock.get(ESPACE_CLIENT_URL, json=ESPACE_CLIENT_PAYLOAD)
    aioclient_mock.get(FACTURATION_URL, json=FACTURATION_PAYLOAD)

    result = await api.login()

    assert result is True
    assert api.account_data.access_token == "tok-123"
    assert api.account_data.id_abonnement == ACCOUNT_ID
    assert api.account_data.tiers_id == "tiers-99"
    assert api.account_data.contact_id == "contact-99"
    assert api.account_data.numero_compteur == "U24BA285500"
    assert api.account_data.numero_pds == NUMERO_PDS
    assert api.account_data.solde == 12.5
    assert api.account_data.date_debut_abonnement == "2018-08-01"


async def test_login_invalid_credentials(
    api: VeoliaAPI, aioclient_mock: AiohttpClientMocker
) -> None:
    """A Cognito NotAuthorizedException maps to VeoliaAPIInvalidCredentialsError."""
    aioclient_mock.post(
        LOGIN_URL,
        status=400,
        json={
            "__type": "NotAuthorizedException",
            "message": "Incorrect username or password.",
        },
    )

    with pytest.raises(VeoliaAPIInvalidCredentialsError):
        await api.login()


async def test_login_missing_credentials_raises() -> None:
    """Missing username/password raises before any network call."""
    api = VeoliaAPI("", "")
    with pytest.raises(VeoliaAPIInvalidCredentialsError):
        await api.login()
    await api.close()


async def test_login_invalid_email_format_raises() -> None:
    """A malformed email address raises before any network call."""
    api = VeoliaAPI("not-an-email", "secret")
    with pytest.raises(VeoliaAPIInvalidCredentialsError):
        await api.login()
    await api.close()


async def test_401_outside_login_raises_token_error(
    api: VeoliaAPI, aioclient_mock: AiohttpClientMocker
) -> None:
    """A 401 on a non-login request raises VeoliaAPITokenError."""
    api.account_data.access_token = "already-authenticated"  # noqa: S105
    api.account_data.token_expiration = (
        datetime.now(UTC) + timedelta(hours=1)
    ).timestamp()
    api.account_data.id_abonnement = ACCOUNT_ID
    api.account_data.numero_pds = NUMERO_PDS

    aioclient_mock.get(ALERTES_URL, status=401)

    with pytest.raises(VeoliaAPITokenError):
        await api.get_alerts_settings()


async def test_429_is_retried_then_succeeds(
    api: VeoliaAPI,
    aioclient_mock: AiohttpClientMocker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 429 response is retried by tenacity and eventually succeeds."""
    # Avoid a real exponential-backoff sleep between retry attempts.
    monkeypatch.setattr(
        VeoliaAPI._send_request.retry,  # noqa: SLF001
        "wait",
        tenacity.wait_none(),
    )

    api.account_data.access_token = "already-authenticated"  # noqa: S105
    api.account_data.token_expiration = (
        datetime.now(UTC) + timedelta(hours=1)
    ).timestamp()
    api.account_data.id_abonnement = ACCOUNT_ID
    api.account_data.numero_pds = NUMERO_PDS

    calls = {"count": 0}

    async def _side_effect(
        method: str, url: str, data: object
    ) -> AiohttpClientMockResponse:
        calls["count"] += 1
        if calls["count"] == 1:
            return AiohttpClientMockResponse(method=method, url=url, status=429)
        return AiohttpClientMockResponse(method=method, url=url, status=204)

    aioclient_mock.get(ALERTES_URL, side_effect=_side_effect)

    settings = await api.get_alerts_settings()

    assert calls["count"] == 2
    assert settings.daily_enabled is False


async def test_get_alerts_settings_204_defaults_disabled(
    api: VeoliaAPI, aioclient_mock: AiohttpClientMocker
) -> None:
    """A 204 (no alerts configured) maps to a fully-disabled AlertSettings."""
    api.account_data.access_token = "already-authenticated"  # noqa: S105
    api.account_data.token_expiration = (
        datetime.now(UTC) + timedelta(hours=1)
    ).timestamp()
    api.account_data.id_abonnement = ACCOUNT_ID
    api.account_data.numero_pds = NUMERO_PDS
    aioclient_mock.get(ALERTES_URL, status=204)

    settings = await api.get_alerts_settings()

    assert settings == AlertSettings(
        daily_enabled=False,
        daily_threshold=0,
        daily_notif_email=False,
        daily_notif_sms=False,
        monthly_enabled=False,
        monthly_threshold=0,
        monthly_notif_email=False,
        monthly_notif_sms=False,
    )


async def test_get_alerts_settings_200_with_active_alerts(
    api: VeoliaAPI, aioclient_mock: AiohttpClientMocker
) -> None:
    """A 200 response with actual thresholds is parsed into AlertSettings."""
    api.account_data.access_token = "already-authenticated"  # noqa: S105
    api.account_data.token_expiration = (
        datetime.now(UTC) + timedelta(hours=1)
    ).timestamp()
    api.account_data.id_abonnement = ACCOUNT_ID
    api.account_data.numero_pds = NUMERO_PDS
    aioclient_mock.get(
        ALERTES_URL,
        json={
            "seuils": {
                "journalier": {
                    "valeur": 150,
                    "unite": "L",
                    "moyen_contact": {
                        "souscrit_par_email": True,
                        "souscrit_par_mobile": True,
                    },
                },
                "mensuel": {
                    "valeur": 5,
                    "unite": "M3",
                    "moyen_contact": {
                        "souscrit_par_email": True,
                        "souscrit_par_mobile": False,
                    },
                },
            }
        },
    )

    settings = await api.get_alerts_settings()

    assert settings == AlertSettings(
        daily_enabled=True,
        daily_threshold=150,
        daily_notif_email=True,
        daily_notif_sms=True,
        monthly_enabled=True,
        monthly_threshold=5,
        monthly_notif_email=True,
        monthly_notif_sms=False,
    )


async def test_get_alerts_settings_error_status_raises(
    api: VeoliaAPI, aioclient_mock: AiohttpClientMocker
) -> None:
    """A non-200/204 response on the alertes GET endpoint raises."""
    api.account_data.access_token = "already-authenticated"  # noqa: S105
    api.account_data.token_expiration = (
        datetime.now(UTC) + timedelta(hours=1)
    ).timestamp()
    api.account_data.id_abonnement = ACCOUNT_ID
    api.account_data.numero_pds = NUMERO_PDS
    aioclient_mock.get(ALERTES_URL, status=500)

    with pytest.raises(VeoliaAPIGetDataError, match="alertes"):
        await api.get_alerts_settings()


async def test_set_alerts_settings_204_returns_true(
    api: VeoliaAPI, aioclient_mock: AiohttpClientMocker
) -> None:
    """A 204 response on the alertes POST endpoint means success."""
    api.account_data.access_token = "already-authenticated"  # noqa: S105
    api.account_data.token_expiration = (
        datetime.now(UTC) + timedelta(hours=1)
    ).timestamp()
    api.account_data.id_abonnement = ACCOUNT_ID
    api.account_data.numero_pds = NUMERO_PDS
    api.account_data.contact_id = "contact-99"
    api.account_data.tiers_id = "tiers-99"
    api.account_data.numero_compteur = "U24BA285500"
    aioclient_mock.post(ALERTES_URL, status=204)

    settings = AlertSettings(
        daily_enabled=True,
        daily_threshold=150,
        daily_notif_email=True,
        daily_notif_sms=False,
        monthly_enabled=True,
        monthly_threshold=5,
        monthly_notif_email=True,
        monthly_notif_sms=False,
    )
    result = await api.set_alerts_settings(settings)

    assert result is True
    _method, _url, payload, _headers = aioclient_mock.mock_calls[-1]
    assert payload["alerte_journaliere"]["seuil"] == 150
    assert payload["alerte_mensuelle"]["seuil"] == 5
    assert payload["abo_id"] == ACCOUNT_ID


async def test_set_alerts_settings_error_status_raises(
    api: VeoliaAPI, aioclient_mock: AiohttpClientMocker
) -> None:
    """A non-204 response on the alertes POST endpoint raises."""
    api.account_data.access_token = "already-authenticated"  # noqa: S105
    api.account_data.token_expiration = (
        datetime.now(UTC) + timedelta(hours=1)
    ).timestamp()
    api.account_data.id_abonnement = ACCOUNT_ID
    api.account_data.numero_pds = NUMERO_PDS
    aioclient_mock.post(ALERTES_URL, status=400)

    settings = AlertSettings(
        daily_enabled=False,
        daily_threshold=0,
        daily_notif_email=False,
        daily_notif_sms=False,
        monthly_enabled=False,
        monthly_threshold=0,
        monthly_notif_email=False,
        monthly_notif_sms=False,
    )
    with pytest.raises(VeoliaAPISetDataError):
        await api.set_alerts_settings(settings)


async def test_fetch_all_data_aggregates_monthly_and_daily(
    api: VeoliaAPI, aioclient_mock: AiohttpClientMocker
) -> None:
    """fetch_all_data aggregates yearly/monthly consumption and side data."""
    api.account_data.access_token = "already-authenticated"  # noqa: S105
    api.account_data.token_expiration = (
        datetime.now(UTC) + timedelta(hours=1)
    ).timestamp()
    api.account_data.id_abonnement = ACCOUNT_ID
    api.account_data.numero_pds = NUMERO_PDS
    api.account_data.date_debut_abonnement = "2018-08-01"

    aioclient_mock.get(
        MENSUELLES_URL,
        json=[{"annee": 2026, "mois": 7, "consommation": {"m3": 3.4}}],
    )
    aioclient_mock.get(
        JOURNALIERES_URL,
        json=[
            {
                "date_releve": "2026-07-08",
                "consommation": {"litre": 120, "m3": 0.12},
                "index": {"m3": 337.2},
                "fiabilite_index": "MESURE",
            }
        ],
    )
    aioclient_mock.get(MENSUALISATION_URL, json={"prelevements_echeancier": []})
    aioclient_mock.get(ALERTES_URL, status=204)

    await api.fetch_all_data(date(2026, 7, 1), date(2026, 7, 1))

    assert api.account_data.monthly_consumption == [
        {"annee": 2026, "mois": 7, "consommation": {"m3": 3.4}}
    ]
    assert len(api.account_data.daily_consumption) == 1
    assert api.account_data.billing_plan == {"prelevements_echeancier": []}
    assert api.account_data.alert_settings.daily_enabled is False


async def test_fetch_all_data_skips_requests_before_subscription_start(
    api: VeoliaAPI, aioclient_mock: AiohttpClientMocker
) -> None:
    """No consumption data is requested for periods before the subscription start."""
    api.account_data.access_token = "already-authenticated"  # noqa: S105
    api.account_data.token_expiration = (
        datetime.now(UTC) + timedelta(hours=1)
    ).timestamp()
    api.account_data.id_abonnement = ACCOUNT_ID
    api.account_data.numero_pds = NUMERO_PDS
    # Subscription starts after the requested period: both the yearly and
    # monthly requests should be skipped entirely (no HTTP call needed).
    api.account_data.date_debut_abonnement = "2026-08-01"

    aioclient_mock.get(MENSUALISATION_URL, status=204)
    aioclient_mock.get(ALERTES_URL, status=204)

    await api.fetch_all_data(date(2026, 7, 1), date(2026, 7, 1))

    assert api.account_data.monthly_consumption == []
    assert api.account_data.daily_consumption == []


async def test_close_closes_owned_session() -> None:
    """close() closes a session the client created itself."""
    api = VeoliaAPI(USERNAME, PASSWORD)
    assert api.session.closed is False
    await api.close()
    assert api.session.closed is True


async def test_close_does_not_close_injected_session() -> None:
    """close() must not close a session that was injected by the caller."""
    injected_session = MagicMock()
    injected_session.closed = False
    injected_session.close = AsyncMock()
    api = VeoliaAPI(USERNAME, PASSWORD, session=injected_session)

    await api.close()

    injected_session.close.assert_not_awaited()


async def test_unknown_portal_raises_value_error() -> None:
    """Constructing the client with an unsupported portal raises ValueError."""
    with pytest.raises(ValueError, match="Unknown Veolia portal"):
        VeoliaAPI(USERNAME, PASSWORD, portal_url="not-a-real-portal.example")
