"""Tests for the pure helper functions in helpers.py."""

from __future__ import annotations

from custom_components.veolia.helpers import is_unoccupied_mode

from .const import build_alert_settings


def test_is_unoccupied_mode_true_when_daily_enabled_and_threshold_zero() -> None:
    """Unoccupied mode is a daily alert enabled with a zero threshold."""
    settings = build_alert_settings(daily_enabled=True, daily_threshold=0)
    assert is_unoccupied_mode(settings) is True


def test_is_unoccupied_mode_false_when_threshold_nonzero() -> None:
    """A non-zero threshold is a regular daily alert, not unoccupied mode."""
    settings = build_alert_settings(daily_enabled=True, daily_threshold=150)
    assert is_unoccupied_mode(settings) is False


def test_is_unoccupied_mode_false_when_daily_disabled() -> None:
    """Unoccupied mode requires the daily alert to be enabled."""
    settings = build_alert_settings(daily_enabled=False, daily_threshold=0)
    assert is_unoccupied_mode(settings) is False


def test_is_unoccupied_mode_false_when_daily_disabled_and_nonzero_threshold() -> None:
    """Neither condition holds: not unoccupied mode."""
    settings = build_alert_settings(daily_enabled=False, daily_threshold=150)
    assert is_unoccupied_mode(settings) is False
