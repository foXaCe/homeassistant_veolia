"""Constants for the Veolia API."""

from __future__ import annotations

from enum import Enum
from typing import Final

# Cognito authentication endpoint (region eu-west-3).
LOGIN_URL: Final = "https://cognito-idp.eu-west-3.amazonaws.com"

TYPE_FRONT: Final = "WEB_ORDINATEUR"

# HTTP Methods
GET: Final = "GET"
POST: Final = "POST"

# AsyncIO HTTP/Session
TIMEOUT: Final = 15
CONCURRENTS_TASKS: Final = 3
# Re-login this many seconds before the token actually expires.
TOKEN_EXPIRY_MARGIN: Final = 60


class ConsumptionType(Enum):
    """Consumption type."""

    MONTHLY = "monthly"
    YEARLY = "yearly"
