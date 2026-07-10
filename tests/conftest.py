"""Shared fixtures for the Veolia integration test suite.

Ordering note: tests that set up the config entry (directly, or indirectly
via a config/options flow) must request ``recorder_mock`` *before* ``hass``
in their signature, e.g.::

    async def test_x(recorder_mock: Recorder, hass: HomeAssistant, ...):

The ``veolia`` manifest depends on ``recorder``, so Home Assistant will try
to set up the real recorder component as soon as the entry is set up unless
the in-memory ``recorder_mock`` is already active. Because ``recorder_mock``
itself needs ``hass`` as one of its own dependencies, and pytest resolves a
fixture's own dependencies before moving to the next argument, requesting it
first guarantees the in-memory recorder wins the race. An *autouse* fixture
that depends on ``hass`` (e.g. a naive ``enable_custom_integrations``
wrapper) would instead force ``hass`` to be created first regardless of
argument order, so ``enable_custom_integrations`` is intentionally requested
explicitly, per test, and listed last.
"""

from __future__ import annotations

from collections.abc import Generator
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.veolia.const import DOMAIN

from .const import MOCK_ACCOUNT_ID, MOCK_CONFIG_ENTRY_DATA, build_account_data

pytest_plugins = "pytest_homeassistant_custom_component"

# The in-memory recorder is very chatty at DEBUG/INFO; keep test output readable.
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a fully migrated (v2) mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id=MOCK_ACCOUNT_ID,
        data=dict(MOCK_CONFIG_ENTRY_DATA),
        entry_id="test_entry_id",
    )


@pytest.fixture
def mock_veolia_api() -> Generator[MagicMock]:
    """Mock the vendored VeoliaAPI client at its three usage points.

    The class is patched in coordinator.py (runtime), config_flow.py (config
    and options flows) and __init__.py (v1 -> v2 migration), each returning
    the same MagicMock instance so tests can assert on a single object.
    """
    account_data = build_account_data()
    api = MagicMock(name="VeoliaAPI")
    api.account_data = account_data
    api.username = MOCK_CONFIG_ENTRY_DATA["username"]
    api.password = MOCK_CONFIG_ENTRY_DATA["password"]
    api.login = AsyncMock(return_value=True)
    api.fetch_all_data = AsyncMock(return_value=None)
    api.get_alerts_settings = AsyncMock(return_value=account_data.alert_settings)
    api.set_alerts_settings = AsyncMock(return_value=True)
    api.close = AsyncMock(return_value=None)

    with (
        patch(
            "custom_components.veolia.coordinator.VeoliaAPI", return_value=api
        ) as coordinator_cls,
        patch(
            "custom_components.veolia.config_flow.VeoliaAPI", return_value=api
        ) as config_flow_cls,
        patch("custom_components.veolia.VeoliaAPI", return_value=api) as init_cls,
    ):
        api.coordinator_cls = coordinator_cls
        api.config_flow_cls = config_flow_cls
        api.init_cls = init_cls
        yield api
