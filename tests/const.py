"""Shared test data for the Veolia integration test suite."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from custom_components.veolia.veolia_api.model import AlertSettings, VeoliaAccountData

MOCK_USERNAME = "test@example.com"
MOCK_PASSWORD = "secret"
MOCK_ACCOUNT_ID = "1235075"
MOCK_NUMERO_PDS = "001OVAH"
MOCK_NUMERO_COMPTEUR = "U24BA285500"

MOCK_CONFIG_ENTRY_DATA: dict[str, Any] = {
    "username": MOCK_USERNAME,
    "password": MOCK_PASSWORD,
    "portal_url": None,
}

# Daily consumption fixture: a gap between 07-01 and 07-03 exercises the
# forward-fill behaviour of `_compute_index_stats`.
DAILY_CONSUMPTION: list[dict[str, Any]] = [
    {
        "date_releve": "2026-07-01",
        "consommation": {"litre": 100, "m3": 0.1},
        "index": {"m3": 337.0},
        "fiabilite_index": "MESURE",
    },
    {
        "date_releve": "2026-07-03",
        "consommation": {"litre": 110, "m3": 0.11},
        "index": {"m3": 337.1},
        "fiabilite_index": "MESURE",
    },
    {
        "date_releve": "2026-07-08",
        "consommation": {"litre": 120, "m3": 0.12},
        "index": {"m3": 337.2},
        "fiabilite_index": "MESURE",
    },
]

MONTHLY_CONSUMPTION: list[dict[str, Any]] = [
    {
        "annee": 2025,
        "mois": 7,
        "consommation": {"m3": 3.0},
        "fiabilite_conso": "MESURE",
    },
    {
        "annee": 2026,
        "mois": 6,
        "consommation": {"m3": 3.2},
        "fiabilite_conso": "MESURE",
    },
    {
        "annee": 2026,
        "mois": 7,
        "consommation": {"m3": 3.4},
        "fiabilite_conso": "MESURE",
    },
]

BILLING_PLAN: dict[str, Any] = {
    "prelevements_echeancier": [
        {"date": "2026-06-15", "montant": 45.0, "etat_prelevement": "DONE"},
        {"date": "2026-07-15", "montant": 45.0, "etat_prelevement": "WAITING"},
    ]
}


def build_alert_settings(**overrides: Any) -> AlertSettings:
    """Build a realistic AlertSettings instance for tests."""
    values: dict[str, Any] = {
        "daily_enabled": True,
        "daily_threshold": 150,
        "daily_notif_email": True,
        "daily_notif_sms": False,
        "monthly_enabled": True,
        "monthly_threshold": 5,
        "monthly_notif_email": True,
        "monthly_notif_sms": False,
    }
    values.update(overrides)
    return AlertSettings(**values)


def build_account_data(**overrides: Any) -> VeoliaAccountData:
    """Build a realistic VeoliaAccountData instance for tests."""
    data = VeoliaAccountData(
        access_token="access-token",  # noqa: S106
        token_expiration=9999999999,
        id_abonnement=MOCK_ACCOUNT_ID,
        numero_pds=MOCK_NUMERO_PDS,
        contact_id="contact-1",
        tiers_id="tiers-1",
        numero_compteur=MOCK_NUMERO_COMPTEUR,
        date_debut_abonnement="2018-08-01",
        solde=12.5,
        dernier_index_releve=337.0,
        date_index_releve="2026-07-08",
        mode_releve="TELERELEVE",
        mode_paiement="PRELEVEMENT",
        numero_client="CLIENT-1",
        titulaire="M. Test",
        marque="ITRON",
        adresse_de_branchement="1 rue de Test",
        emplacement_compteur="Cave",
        libelle_contrat="Contrat eau",
        statut="ACTIF",
        monthly_consumption=deepcopy(MONTHLY_CONSUMPTION),
        daily_consumption=deepcopy(DAILY_CONSUMPTION),
        alert_settings=build_alert_settings(),
        billing_plan=deepcopy(BILLING_PLAN),
    )
    for key, value in overrides.items():
        setattr(data, key, value)
    return data


# Commune reference API fixtures.
MOCK_POSTAL_CODE = "75001"

COMMUNE_DIRECT: dict[str, Any] = {
    "libelle": "PARIS 1ER ARRONDISSEMENT",
    "type_commune": "NON_REDIRIGE",
}

COMMUNE_REDIRECTED_SUPPORTED: dict[str, Any] = {
    "libelle": "PERPIGNAN",
    "type_commune": "REDIRIGE",
    "url_redirection": "https://www.ea-pm.fr/login",
}

COMMUNE_REDIRECTED_UNSUPPORTED: dict[str, Any] = {
    "libelle": "AUTRE VILLE",
    "type_commune": "REDIRIGE",
    "url_redirection": "https://www.unknown-portal.fr/login",
}

COMMUNE_NOT_SERVED: dict[str, Any] = {
    "libelle": "VILLE SANS VEOLIA",
    "type_commune": "NON_DESSERVIE",
}
