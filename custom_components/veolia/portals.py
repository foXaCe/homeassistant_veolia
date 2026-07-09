"""Portails Veolia additionnels non (encore) fournis par veolia_api.

Le client `veolia_api` maintient la liste des portails supportés dans
`veolia_api.portals.VEOLIA_PORTAL_CLIENTS` (mapping hostname -> client_id
AWS Cognito) et un backend unique codé en dur (`BACKEND_ISTEFR`).

Certains portails délégués (ex. Eau de Perpignan Méditerranée Métropole)
partagent le même mécanisme d'authentification Cognito mais exposent leurs
données sur un backend différent (`prd-ael-sirius-pmm-backend` au lieu de
`prd-ael-sirius-backend`). Ce module enregistre ces portails communautaires
au chargement de l'intégration, avec leur `client_id` et leur backend, sans
attendre une nouvelle release du client.

Le `client_id` d'un portail se trouve dans le bundle JavaScript du site
(`ClientId:"..."`) ; le backend dans les appels réseau vers `*.istefr.fr`.
"""

from __future__ import annotations

from veolia_api.constants import BACKEND_ISTEFR as DEFAULT_BACKEND_URL
from veolia_api.portals import VEOLIA_PORTAL_CLIENTS

from .const import LOGGER

# hostname (tel que renvoyé par l'API communes dans url_redirection) -> config
EXTRA_PORTALS: dict[str, dict[str, str]] = {
    # Eau de Perpignan Méditerranée Métropole (Eau Agglo)
    "www.ea-pm.fr": {
        "client_id": "54e8dri103e65defj6p67eolli",
        "backend_url": "https://prd-ael-sirius-pmm-backend.istefr.fr",
    },
}


def register_extra_portals() -> None:
    """Enregistre les portails additionnels dans veolia_api (idempotent)."""
    for hostname, config in EXTRA_PORTALS.items():
        client_id = config["client_id"]
        if VEOLIA_PORTAL_CLIENTS.get(hostname) != client_id:
            VEOLIA_PORTAL_CLIENTS[hostname] = client_id
            LOGGER.debug("Registered extra Veolia portal: %s", hostname)


def get_backend_url(portal_url: str | None) -> str:
    """Retourne le backend à utiliser pour un portail donné.

    Les portails additionnels peuvent avoir leur propre backend ; les autres
    utilisent le backend par défaut de `veolia_api`.
    """
    config = EXTRA_PORTALS.get(portal_url or "")
    if config and "backend_url" in config:
        return config["backend_url"]
    return DEFAULT_BACKEND_URL


register_extra_portals()
