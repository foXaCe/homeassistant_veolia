"""Client Veolia sensible au portail.

`veolia_api.VeoliaAPI` cible un backend unique (`BACKEND_ISTEFR`). Certains
portails délégués exposent leurs données sur un autre backend tout en
partageant le même flux d'authentification Cognito (cf. [portals][portals]).

`PortalVeoliaAPI` redirige, **par instance**, les appels vers le backend du
portail configuré. Tous les appels de données de `veolia_api` passent par
`_send_request`, on réécrit donc uniquement l'hôte du backend par défaut vers
celui du portail — sans toucher à l'URL d'authentification Cognito ni dupliquer
les chemins d'endpoints.

[portals]: portals.py
"""

from __future__ import annotations

from typing import Any

from veolia_api import VeoliaAPI
from veolia_api.constants import BACKEND_ISTEFR as DEFAULT_BACKEND_URL


class PortalVeoliaAPI(VeoliaAPI):
    """`VeoliaAPI` dont le backend de données est choisi par portail."""

    def __init__(
        self,
        *args: Any,
        backend_url: str = DEFAULT_BACKEND_URL,
        **kwargs: Any,
    ) -> None:
        """Initialise le client avec le backend du portail."""
        super().__init__(*args, **kwargs)
        self._backend_url = backend_url

    async def _send_request(self, url: str, *args: Any, **kwargs: Any) -> Any:
        """Réécrit l'hôte du backend par défaut vers celui du portail."""
        if self._backend_url != DEFAULT_BACKEND_URL and url.startswith(
            DEFAULT_BACKEND_URL,
        ):
            url = self._backend_url + url[len(DEFAULT_BACKEND_URL) :]
        return await super()._send_request(url, *args, **kwargs)
