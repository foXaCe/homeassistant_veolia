"""Constants for the Veolia API."""

from enum import Enum

from .portals import DEFAULT_BACKEND_URL, DEFAULT_PORTAL_URL, VEOLIA_PORTALS

# URLS
LOGIN_URL = "https://cognito-idp.eu-west-3.amazonaws.com"
# Default data backend (national portal). Kept for backward compatibility;
# the effective backend is resolved per portal (see portals.py).
BACKEND_ISTEFR = DEFAULT_BACKEND_URL

# AUTH — default Cognito client id (national portal), for backward compatibility.
LOGIN_CLIENT_ID = VEOLIA_PORTALS[DEFAULT_PORTAL_URL].client_id

# API Flow Endpoints
CALLBACK_ENDPOINT = "/callback"

TYPE_FRONT = "WEB_ORDINATEUR"

# HTTP Methods
GET = "GET"
POST = "POST"

# AsyncIO HTTP/Session
TIMEOUT = 15
CONCURRENTS_TASKS = 3
# Re-login this many seconds before the token actually expires.
TOKEN_EXPIRY_MARGIN = 60


class ConsumptionType(Enum):
    """Consumption type."""

    MONTHLY = "monthly"
    YEARLY = "yearly"
