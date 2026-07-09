"""Supported Veolia portals.

Veolia operates several water-management portals. They all share the same
AWS Cognito authentication flow (region ``eu-west-3``) but each portal has its
own Cognito ``client_id`` and may expose its data on a different backend host.

The national portal (``eau.veolia.fr``) and its delegated brandings (e.g. Eau
de Toulouse Métropole) run on the default backend. Some independent deployments
(e.g. Eau de Perpignan Méditerranée Métropole, ``www.ea-pm.fr``) run on their
own backend.

To add support for a portal, add an entry to :data:`VEOLIA_PORTALS`:

* ``client_id`` — the Cognito app client id, found in the portal's JavaScript
  bundle (``ClientId:"..."``) or in the network traffic when logging in.
* ``backend_url`` — the ``*.istefr.fr`` host serving the account/consumption
  data; omit it when the portal uses the default backend.
"""

from __future__ import annotations

from dataclasses import dataclass

# Default data backend, used by the national portal and its delegated brandings.
DEFAULT_BACKEND_URL = "https://prd-ael-sirius-backend.istefr.fr"

# Default portal, used when no portal is explicitly selected.
DEFAULT_PORTAL_URL = "eau.veolia.fr"


@dataclass(frozen=True)
class VeoliaPortal:
    """Configuration of a Veolia portal."""

    client_id: str
    backend_url: str = DEFAULT_BACKEND_URL


# hostname (as returned by the commune reference API in ``url_redirection``,
# or the portal's own hostname) -> portal configuration.
VEOLIA_PORTALS: dict[str, VeoliaPortal] = {
    "eau.veolia.fr": VeoliaPortal(
        client_id="3kghade1fg54739kj8pkbova8j",
    ),
    "eaudetm.monespace.eau.veolia.fr": VeoliaPortal(
        client_id="19bjc8ldefie683n889iiubjc8",  # Eau de Toulouse Métropole
    ),
    "www.ea-pm.fr": VeoliaPortal(
        client_id="54e8dri103e65defj6p67eolli",  # Eau de Perpignan Méditerranée Métropole
        backend_url="https://prd-ael-sirius-pmm-backend.istefr.fr",
    ),
}

# Backward-compatible mapping hostname -> client_id (kept for consumers that
# only need to test portal support or read the client id).
VEOLIA_PORTAL_CLIENTS: dict[str, str] = {
    hostname: portal.client_id for hostname, portal in VEOLIA_PORTALS.items()
}


def get_portal(portal_url: str | None) -> VeoliaPortal:
    """Return the configuration for ``portal_url`` (or the default portal).

    Raises:
        ValueError: if ``portal_url`` is not a supported portal.

    """
    hostname = portal_url or DEFAULT_PORTAL_URL
    try:
        return VEOLIA_PORTALS[hostname]
    except KeyError:
        raise ValueError(
            f"Unknown Veolia portal: {hostname!r}. "
            f"Add it to VEOLIA_PORTALS in portals.py",
        ) from None
