"""Constants for veolia."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "veolia"
NAME = "Veolia"
CONF_PORTAL_URL = "portal_url"

# Options
DEFAULT_SCAN_INTERVAL_HOURS = 6

# Commune lookup endpoint used by the config flow to check eligibility.
COMMUNES_LOOKUP_URL = "https://prd-ael-sirius-refcommunes.istefr.fr/communes-nationales"

# API constants keys
LAST_DATA = -1
IDX = "index"
LITRE = "litre"
CUBIC_METER = "m3"
CONSO = "consommation"
IDX_FIABILITY = "fiabilite_index"
CONSO_FIABILITY = "fiabilite_conso"
DATA_DATE = "date_releve"
YEAR = "annee"
MONTH = "mois"
