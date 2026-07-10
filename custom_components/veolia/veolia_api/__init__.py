"""Vendored Veolia API client.

Copie intégrée du client [veolia-api](https://github.com/foXaCe/veolia-api)
(fork de https://github.com/Jezza34000/veolia-api, licence MIT).

Cette copie est embarquée dans l'intégration car Home Assistant (hassfest)
n'accepte que des dépendances PyPI dans ``manifest.json`` : le fork corrigé
(résolution du ``client_id`` et du backend par portail) n'étant pas publié sur
PyPI, il est vendoré ici. Voir NOTICE dans ce dossier.

Ne modifiez pas ce code directement : reportez les correctifs sur le fork puis
resynchronisez.
"""

from __future__ import annotations

from .portals import VEOLIA_PORTAL_CLIENTS, VEOLIA_PORTALS, VeoliaPortal
from .veolia_api import VeoliaAPI

__all__ = [
    "VEOLIA_PORTALS",
    "VEOLIA_PORTAL_CLIENTS",
    "VeoliaAPI",
    "VeoliaPortal",
]

__version__ = "2.2.3"
