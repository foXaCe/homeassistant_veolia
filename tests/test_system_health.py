"""Tests for the Veolia system health."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock

import aiohttp
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    get_system_health_info,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from veolia_api.portals import DEFAULT_PORTAL_URL

from custom_components.veolia.const import DOMAIN
from homeassistant.components.recorder import Recorder
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component


async def _resolved_info(hass: HomeAssistant) -> dict[str, Any]:
    """Return the system health info with awaitable values resolved."""
    info = await get_system_health_info(hass, DOMAIN)
    return {
        key: (await value) if asyncio.iscoroutine(value) else value
        for key, value in info.items()
    }


async def test_system_health_reachable(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A loaded entry reports its account, refresh health and reachable portal."""
    assert await async_setup_component(hass, "system_health", {})
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    aioclient_mock.get(f"https://{DEFAULT_PORTAL_URL}", text="")
    info = await _resolved_info(hass)

    assert info == {
        "configured_accounts": 1,
        "last_update_success": True,
        "can_reach_server": "ok",
    }


async def test_system_health_unreachable(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    mock_veolia_api: MagicMock,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A network failure toward the portal is reported as unreachable."""
    assert await async_setup_component(hass, "system_health", {})
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    aioclient_mock.get(f"https://{DEFAULT_PORTAL_URL}", exc=aiohttp.ClientError("boom"))
    info = await _resolved_info(hass)

    assert info["configured_accounts"] == 1
    assert info["can_reach_server"] == {"type": "failed", "error": "unreachable"}
