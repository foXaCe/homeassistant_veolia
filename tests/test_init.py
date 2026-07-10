"""Tests for the Veolia integration setup, unload and migration."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from veolia_api.exceptions import VeoliaAPIError, VeoliaAPIInvalidCredentialsError

from custom_components.veolia import async_migrate_entry
from custom_components.veolia.const import DOMAIN
from homeassistant.components.recorder import Recorder
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import MOCK_ACCOUNT_ID, MOCK_CONFIG_ENTRY_DATA


async def test_setup_and_unload_entry(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """A config entry sets up cleanly and unloads without leftovers."""
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.runtime_data is not None

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_entry_not_ready_on_api_error(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """A VeoliaAPIError on the first refresh triggers a setup retry."""
    mock_veolia_api.fetch_all_data.side_effect = VeoliaAPIError("boom")
    mock_config_entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_entry_auth_failed_starts_reauth(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
) -> None:
    """Invalid credentials on the first refresh trigger the reauth flow."""
    mock_veolia_api.fetch_all_data.side_effect = VeoliaAPIInvalidCredentialsError(
        "bad creds"
    )
    mock_config_entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == "reauth"
    assert flows[0]["context"]["entry_id"] == mock_config_entry.entry_id


async def test_migration_v1_to_v2(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_veolia_api: MagicMock,
) -> None:
    """A v1 entry is fully migrated: unique ids, device identifiers, entry id."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        unique_id=None,
        data=dict(MOCK_CONFIG_ENTRY_DATA),
        entry_id="legacy_entry_id",
    )
    entry.add_to_hass(hass)

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer="Veolia",
        name="Veolia legacy",
    )

    entity_registry = er.async_get(hass)
    legacy_unique_ids = ["daily_consumption", "last_index", "balance"]
    for key in legacy_unique_ids:
        entity_registry.async_get_or_create(
            "sensor",
            DOMAIN,
            f"{entry.entry_id}_{key}",
            config_entry=entry,
            device_id=device.id,
        )
    # An entity whose unique_id does not follow the legacy {entry_id}_{key}
    # pattern is left untouched by the migration (covers the "no match" path).
    entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "already_account_scoped_unique_id",
        config_entry=entry,
        device_id=device.id,
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 2
    assert entry.unique_id == MOCK_ACCOUNT_ID
    assert entry.state is ConfigEntryState.LOADED

    for key in legacy_unique_ids:
        assert (
            entity_registry.async_get_entity_id(
                "sensor", DOMAIN, f"{entry.entry_id}_{key}"
            )
            is None
        )
        new_entity_id = entity_registry.async_get_entity_id(
            "sensor", DOMAIN, f"{MOCK_ACCOUNT_ID}_{key}"
        )
        assert new_entity_id is not None

    migrated_device = device_registry.async_get_device(
        identifiers={(DOMAIN, MOCK_ACCOUNT_ID)}
    )
    assert migrated_device is not None
    assert migrated_device.id == device.id
    assert (
        device_registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)}) is None
    )

    # The non-matching entity keeps its unique_id unchanged.
    assert (
        entity_registry.async_get_entity_id(
            "sensor", DOMAIN, "already_account_scoped_unique_id"
        )
        is not None
    )


async def test_migration_v1_login_failure_returns_false(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_veolia_api: MagicMock,
) -> None:
    """A failed login during migration aborts and leaves the entry to retry."""
    mock_veolia_api.login.side_effect = VeoliaAPIInvalidCredentialsError("bad creds")
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        unique_id=None,
        data=dict(MOCK_CONFIG_ENTRY_DATA),
        entry_id="legacy_entry_id",
    )
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 1
    assert entry.state is ConfigEntryState.MIGRATION_ERROR


async def test_migration_v1_login_ok_but_no_account_id_returns_false(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_veolia_api: MagicMock,
) -> None:
    """A successful login without an account id aborts the migration."""
    mock_veolia_api.account_data.id_abonnement = None
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        unique_id=None,
        data=dict(MOCK_CONFIG_ENTRY_DATA),
        entry_id="legacy_entry_id",
    )
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 1
    assert entry.state is ConfigEntryState.MIGRATION_ERROR


@pytest.mark.parametrize("future_version", [3, 99])
async def test_migration_from_future_version_fails(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_veolia_api: MagicMock,
    future_version: int,
) -> None:
    """Downgrading from a future config entry version is not supported.

    Home Assistant itself refuses to call ``async_migrate_entry`` when
    ``entry.version`` is already higher than the integration's current
    ``VERSION`` (see ``ConfigEntry.async_migrate`` in config_entries.py), so
    the setup path alone never exercises our own defensive check. Call the
    migration function directly to cover it.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=future_version,
        unique_id=MOCK_ACCOUNT_ID,
        data=dict(MOCK_CONFIG_ENTRY_DATA),
        entry_id="future_entry_id",
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry) is False

    # Also confirm the real setup path independently ends up in an error
    # state (Home Assistant's own version guard, not ours).
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.MIGRATION_ERROR
