"""Pure helper functions for the Veolia integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .veolia_api.model import AlertSettings


def is_unoccupied_mode(settings: AlertSettings) -> bool:
    """Return True when the unoccupied-home alert mode is active.

    Veolia models this mode as a daily alert with a threshold of zero, which
    supersedes the regular daily/monthly alert configuration.
    """
    return bool(settings.daily_enabled) and settings.daily_threshold == 0
