"""Custom types for Veolia."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .coordinator import VeoliaDataUpdateCoordinator

type VeoliaConfigEntry = ConfigEntry[VeoliaDataUpdateCoordinator]
