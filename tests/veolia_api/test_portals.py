"""Tests for the vendored Veolia portals registry."""

from __future__ import annotations

import pytest

from custom_components.veolia.veolia_api.portals import (
    DEFAULT_BACKEND_URL,
    DEFAULT_PORTAL_URL,
    VEOLIA_PORTAL_CLIENTS,
    VEOLIA_PORTALS,
    get_portal,
)


def test_get_portal_none_returns_default() -> None:
    """No portal_url resolves to the default (national) portal."""
    portal = get_portal(None)
    assert portal == VEOLIA_PORTALS[DEFAULT_PORTAL_URL]
    assert portal.backend_url == DEFAULT_BACKEND_URL


def test_get_portal_default_hostname_explicit() -> None:
    """Explicitly requesting the default hostname returns the same portal."""
    assert get_portal(DEFAULT_PORTAL_URL) == get_portal(None)


def test_get_portal_custom_backend() -> None:
    """A portal with a dedicated backend (Perpignan) returns its own URL."""
    portal = get_portal("www.ea-pm.fr")
    assert portal.client_id == "54e8dri103e65defj6p67eolli"
    assert portal.backend_url == "https://prd-ael-sirius-pmm-backend.istefr.fr"


def test_get_portal_delegated_branding_uses_default_backend() -> None:
    """A delegated branding (Toulouse) uses the default backend URL."""
    portal = get_portal("eaudetm.monespace.eau.veolia.fr")
    assert portal.backend_url == DEFAULT_BACKEND_URL


def test_get_portal_unknown_raises_value_error() -> None:
    """An unsupported portal hostname raises ValueError."""
    with pytest.raises(ValueError, match="Unknown Veolia portal"):
        get_portal("not-a-real-portal.example")


def test_portal_clients_mapping_matches_portals() -> None:
    """VEOLIA_PORTAL_CLIENTS mirrors the client_id of each VEOLIA_PORTALS entry."""
    assert set(VEOLIA_PORTAL_CLIENTS) == set(VEOLIA_PORTALS)
    for hostname, client_id in VEOLIA_PORTAL_CLIENTS.items():
        assert VEOLIA_PORTALS[hostname].client_id == client_id
