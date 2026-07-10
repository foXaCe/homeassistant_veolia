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

# Number of consecutive failed refreshes before a repair issue is raised for
# a persistently unreachable Veolia portal (8 x 6h default scan interval ~=
# 2 days of continuous outage).
CONSECUTIVE_FAILURES_FOR_ISSUE: Final = 8

# Commune lookup endpoint used by the config flow to check eligibility.
COMMUNES_LOOKUP_URL: Final = (
    "https://prd-ael-sirius-refcommunes.istefr.fr/communes-nationales"
)

# Display names of the recorder external statistics. The recorder has no
# translation mechanism for statistic names; the integration only serves the
# French Veolia portals, so the names are French by design.
STATISTIC_NAME_DAILY: Final = "Veolia consommation journalière {account_id}"
STATISTIC_NAME_MONTHLY: Final = "Veolia consommation mensuelle {account_id}"
STATISTIC_NAME_INDEX: Final = "Veolia index compteur {account_id}"

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
