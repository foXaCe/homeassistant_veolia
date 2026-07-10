"""Constants for veolia."""

from __future__ import annotations

from logging import Logger, getLogger
from typing import Final

LOGGER: Logger = getLogger(__package__)

DOMAIN: Final = "veolia"
NAME: Final = "Veolia"
CONF_PORTAL_URL: Final = "portal_url"

# Config flow form keys
CONF_POSTAL_CODE: Final = "postal_code"
CONF_COMMUNE: Final = "commune"

# Commune types returned by the communes reference API
COMMUNE_TYPE_DIRECT: Final = "NON_REDIRIGE"
COMMUNE_TYPE_REDIRECTED: Final = "REDIRIGE"
COMMUNE_TYPE_NOT_SERVED: Final = "NON_DESSERVIE"

# Options
DEFAULT_SCAN_INTERVAL_HOURS: Final = 6

# Commune lookup endpoint used by the config flow to check eligibility.
COMMUNES_LOOKUP_URL: Final = (
    "https://prd-ael-sirius-refcommunes.istefr.fr/communes-nationales"
)

# API constants keys
IDX: Final = "index"
LITRE: Final = "litre"
CUBIC_METER: Final = "m3"
CONSO: Final = "consommation"
IDX_FIABILITY: Final = "fiabilite_index"
CONSO_FIABILITY: Final = "fiabilite_conso"
DATA_DATE: Final = "date_releve"
YEAR: Final = "annee"
MONTH: Final = "mois"
