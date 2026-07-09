"""Veolia data model and derived-value computations.

Pure functions only: no Home Assistant imports, no I/O. Everything here is
computed from the raw account data returned by the API client.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, TypedDict

from .const import (
    CONSO,
    CONSO_FIABILITY,
    CUBIC_METER,
    DATA_DATE,
    IDX,
    IDX_FIABILITY,
    LITRE,
    LOGGER,
    MONTH,
    YEAR,
)


class StatisticsRow(TypedDict):
    """One recorder statistics row (cumulative sum series)."""

    start: datetime
    state: float
    sum: float


def _safe_last(seq: Iterable[Any]) -> Any | None:
    """Return the last item of ``seq``, or None when empty or not a sequence."""
    try:
        s = seq if isinstance(seq, list) else list(seq)
    except TypeError:
        return None
    return s[-1] if s else None


def _parse_date(s: str) -> date | None:
    """Parse an ISO ``YYYY-MM-DD`` string, or None when invalid."""
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=UTC).date()
    except (TypeError, ValueError):
        return None


def _find_last_for_date(
    records: list[dict[str, Any]], d: date
) -> dict[str, Any] | None:
    """Find the most recent record matching date ``d``."""
    for rec in reversed(records or []):
        if _parse_date(rec.get(DATA_DATE, "")) == d:
            return rec
    return None


def _to_float(value: Any) -> float | None:
    """Cast to float, None on failure."""
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _midnight_utc(d: date) -> datetime:
    """Return midnight UTC for calendar date ``d``."""
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def _compute_annual_total(monthly: list[dict[str, Any]], year: int) -> float | None:
    """Sum the monthly consumption (m³) recorded for ``year``."""
    try:
        return float(
            sum(
                float((m.get(CONSO) or {}).get(CUBIC_METER) or 0.0)
                for m in monthly
                if m.get(YEAR) == year
            )
        )
    except (TypeError, ValueError):
        return None


def _compute_daily_stats(daily: list[dict[str, Any]]) -> list[StatisticsRow]:
    """Build cumulative daily-consumption statistics rows (liters)."""
    stats: list[StatisticsRow] = []
    cumul = 0
    for rec in daily:
        d = _parse_date(rec.get(DATA_DATE, ""))
        if d is None:
            continue
        liters = int((rec.get(CONSO) or {}).get(LITRE) or 0)
        cumul += liters
        stats.append({"start": _midnight_utc(d), "state": liters, "sum": cumul})
    return stats


def _compute_monthly_stats(monthly: list[dict[str, Any]]) -> list[StatisticsRow]:
    """Build cumulative monthly-consumption statistics rows (m³)."""
    stats: list[StatisticsRow] = []
    cumul = 0.0
    for rec in monthly:
        year = rec.get(YEAR)
        month = rec.get(MONTH)
        if not year or not month:
            continue
        try:
            start = datetime(int(year), int(month), 1, tzinfo=UTC)
        except (TypeError, ValueError):
            continue
        cubic_meter = float((rec.get(CONSO) or {}).get(CUBIC_METER) or 0)
        cumul += cubic_meter
        stats.append({"start": start, "state": cubic_meter, "sum": cumul})
    return stats


def _compute_index_stats(
    daily: list[dict[str, Any]], today: date
) -> list[StatisticsRow]:
    """Build meter-index statistics rows (m³), forward-filling missing days."""
    stats: list[StatisticsRow] = []
    prev_state: float | None = None
    prev_date: date | None = None
    for record in daily:
        d = _parse_date(record.get(DATA_DATE, ""))
        if d is None:
            continue
        idx = (record.get(IDX) or {}).get(CUBIC_METER)
        cur_state = _to_float(idx)
        if cur_state is None:
            continue
        # Forward-fill the gap between two consecutive readings.
        if prev_date is not None and prev_state is not None:
            for i in range(1, (d - prev_date).days):
                fill = prev_date + timedelta(days=i)
                stats.append(
                    {
                        "start": _midnight_utc(fill),
                        "state": prev_state,
                        "sum": prev_state,
                    }
                )
        stats.append({"start": _midnight_utc(d), "state": cur_state, "sum": cur_state})
        prev_state = cur_state
        prev_date = d
    # Forward-fill from the last reading up to today (inclusive).
    if prev_date is not None and prev_state is not None:
        for i in range(1, (today - prev_date).days + 1):
            fill = prev_date + timedelta(days=i)
            stats.append(
                {"start": _midnight_utc(fill), "state": prev_state, "sum": prev_state}
            )
    return stats


def _compute_billing(
    raw: Any, today: date
) -> tuple[float | None, float | None, date | None, float | None]:
    """Extract balance and upcoming direct debit from the billing plan.

    Returns (balance, monthly_payment, next_payment_date, next_payment_amount).
    """
    balance = _to_float(getattr(raw, "solde", None))
    monthly_payment: float | None = None
    next_payment_date: date | None = None
    next_payment_amount: float | None = None
    try:
        schedule = (getattr(raw, "billing_plan", None) or {}).get(
            "prelevements_echeancier"
        ) or []
        upcoming: list[tuple[date, float | None, str]] = []
        last_amount: float | None = None
        for item in schedule:
            raw_date = item.get("date")
            parsed = None
            if raw_date:
                try:
                    parsed = datetime.fromisoformat(raw_date).date()
                except ValueError:
                    parsed = None
            amount = _to_float(item.get("montant"))
            if amount is not None:
                last_amount = amount
            state = item.get("etat_prelevement", "")
            if parsed and (state == "WAITING" or parsed >= today):
                upcoming.append((parsed, amount, state))
        upcoming.sort(key=lambda x: x[0])
        if upcoming:
            next_payment_date, next_payment_amount, _ = upcoming[0]
        # Mensualité : montant du prochain prélèvement, sinon dernier connu
        monthly_payment = (
            next_payment_amount if next_payment_amount is not None else last_amount
        )
    except Exception as err:  # noqa: BLE001
        LOGGER.debug("Unable to compute billing data: %s", err)
    return balance, monthly_payment, next_payment_date, next_payment_amount


@dataclass(slots=True)
class VeoliaComputed:
    """Veolia computed data."""

    last_index_m3: float | None
    last_daily_liters: int | None
    last_daily_m3: float | None
    monthly_latest_m3: float | None
    annual_total_m3: float | None
    last_date: date | None
    daily_fiability: str | None
    monthly_fiability: str | None
    daily_stats_liters: list[StatisticsRow]
    monthly_stats_cubic_meters: list[StatisticsRow]
    index_stats_m3: list[StatisticsRow]
    daily_today_liters: int | None
    daily_today_m3: float | None
    daily_today_fiability: str | None
    balance: float | None
    monthly_payment: float | None
    next_payment_date: date | None
    next_payment_amount: float | None


@dataclass(slots=True)
class VeoliaModel:
    """Exposed model: raw account data plus computed values."""

    raw: Any  # VeoliaAccountData
    computed: VeoliaComputed

    def __getattr__(self, name: str) -> Any:
        """Proxy unknown attributes to the raw account data."""
        return getattr(self.raw, name)

    @staticmethod
    def from_account_data(raw: Any, *, today: date) -> VeoliaModel:
        """Compute the exposed model from raw account data."""
        daily = raw.daily_consumption or []
        monthly = raw.monthly_consumption or []
        last_daily = _safe_last(daily) or {}
        last_month = _safe_last(monthly) or {}

        last_index_m3 = _to_float(
            (last_daily.get(IDX) or {}).get(CUBIC_METER)
            or (last_month.get(IDX) or {}).get(CUBIC_METER)
        )
        last_daily_conso = last_daily.get(CONSO) or {}
        raw_liters = last_daily_conso.get(LITRE)
        last_daily_liters = int(raw_liters) if raw_liters is not None else None
        last_daily_m3 = _to_float(last_daily_conso.get(CUBIC_METER))
        monthly_latest_m3 = _to_float((last_month.get(CONSO) or {}).get(CUBIC_METER))

        raw_last_date = last_daily.get(DATA_DATE)
        last_date = _parse_date(raw_last_date) if raw_last_date else None

        rec_today = _find_last_for_date(daily, today)
        if rec_today:
            conso_today = rec_today.get(CONSO) or {}
            daily_today_liters = int(conso_today.get(LITRE) or 0)
            daily_today_m3 = float(conso_today.get(CUBIC_METER) or 0.0)
            daily_today_fiability = rec_today.get(IDX_FIABILITY)
        else:
            daily_today_liters = None
            daily_today_m3 = None
            daily_today_fiability = None

        balance, monthly_payment, next_payment_date, next_payment_amount = (
            _compute_billing(raw, today)
        )

        computed = VeoliaComputed(
            last_index_m3=last_index_m3,
            last_daily_liters=last_daily_liters,
            last_daily_m3=last_daily_m3,
            monthly_latest_m3=monthly_latest_m3,
            annual_total_m3=_compute_annual_total(monthly, today.year),
            last_date=last_date,
            daily_fiability=last_daily.get(IDX_FIABILITY),
            monthly_fiability=last_month.get(CONSO_FIABILITY),
            daily_stats_liters=_compute_daily_stats(daily),
            monthly_stats_cubic_meters=_compute_monthly_stats(monthly),
            index_stats_m3=_compute_index_stats(daily, today),
            daily_today_liters=daily_today_liters,
            daily_today_m3=daily_today_m3,
            daily_today_fiability=daily_today_fiability,
            balance=balance,
            monthly_payment=monthly_payment,
            next_payment_date=next_payment_date,
            next_payment_amount=next_payment_amount,
        )
        return VeoliaModel(raw=raw, computed=computed)
