"""Tests for the pure model computations in model.py."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from custom_components.veolia.model import (
    VeoliaModel,
    _compute_annual_total,
    _compute_billing,
    _compute_daily_stats,
    _compute_index_stats,
    _compute_monthly_stats,
    _find_last_for_date,
    _parse_date,
    _safe_last,
    _to_float,
)

from .const import build_account_data

# --------------------------------------------------------------------------
# _parse_date
# --------------------------------------------------------------------------


def test_parse_date_valid() -> None:
    """A well-formed ISO date string is parsed."""
    assert _parse_date("2026-07-08") == date(2026, 7, 8)


@pytest.mark.parametrize("value", ["not-a-date", "2026/07/08", "", "2026-13-40"])
def test_parse_date_invalid_string(value: str) -> None:
    """Invalid strings return None instead of raising."""
    assert _parse_date(value) is None


def test_parse_date_none() -> None:
    """None input returns None (TypeError swallowed)."""
    assert _parse_date(None) is None


# --------------------------------------------------------------------------
# _safe_last
# --------------------------------------------------------------------------


def test_safe_last_returns_last_item() -> None:
    """The last item of a populated list is returned."""
    assert _safe_last([1, 2, 3]) == 3


def test_safe_last_empty_list() -> None:
    """An empty list yields None."""
    assert _safe_last([]) is None


def test_safe_last_generator() -> None:
    """A non-list iterable is consumed and its last item returned."""
    assert _safe_last(x for x in (1, 2, 3)) == 3


def test_safe_last_non_iterable_returns_none() -> None:
    """A non-iterable value (e.g. an int) is handled gracefully."""
    assert _safe_last(42) is None  # type: ignore[arg-type]


def test_safe_last_none() -> None:
    """None is not iterable and yields None."""
    assert _safe_last(None) is None  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# _to_float
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, 1.0),
        (1.5, 1.5),
        ("2.5", 2.5),
        (None, None),
        ("not-a-number", None),
        ([1, 2], None),
    ],
)
def test_to_float(value: object, expected: float | None) -> None:
    """Casts numeric-like values, returns None on failure."""
    assert _to_float(value) == expected


# --------------------------------------------------------------------------
# _find_last_for_date
# --------------------------------------------------------------------------


def test_find_last_for_date_match() -> None:
    """The most recent record matching the date is returned."""
    records = [
        {"date_releve": "2026-07-01", "consommation": {"litre": 1}},
        {"date_releve": "2026-07-02", "consommation": {"litre": 2}},
    ]
    found = _find_last_for_date(records, date(2026, 7, 2))
    assert found is not None
    assert found["consommation"]["litre"] == 2


def test_find_last_for_date_no_match() -> None:
    """No record for the given date returns None."""
    records = [{"date_releve": "2026-07-01", "consommation": {"litre": 1}}]
    assert _find_last_for_date(records, date(2026, 7, 5)) is None


def test_find_last_for_date_empty() -> None:
    """An empty/None record list is handled."""
    assert _find_last_for_date([], date(2026, 7, 5)) is None
    assert _find_last_for_date(None, date(2026, 7, 5)) is None  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# _compute_annual_total
# --------------------------------------------------------------------------


def test_compute_annual_total_sums_matching_year() -> None:
    """Only months for the requested year are summed."""
    monthly = [
        {"annee": 2026, "mois": 1, "consommation": {"m3": 1.0}},
        {"annee": 2026, "mois": 2, "consommation": {"m3": 2.5}},
        {"annee": 2025, "mois": 12, "consommation": {"m3": 100.0}},
    ]
    assert _compute_annual_total(monthly, 2026) == pytest.approx(3.5)


def test_compute_annual_total_empty_list() -> None:
    """An empty list sums to zero."""
    assert _compute_annual_total([], 2026) == 0.0


def test_compute_annual_total_missing_consommation() -> None:
    """Records missing the consommation key contribute zero."""
    monthly = [{"annee": 2026, "mois": 1}]
    assert _compute_annual_total(monthly, 2026) == 0.0


def test_compute_annual_total_invalid_value_returns_none() -> None:
    """A non-numeric consumption value makes the whole computation fail safely."""
    monthly = [{"annee": 2026, "mois": 1, "consommation": {"m3": "not-a-number"}}]
    assert _compute_annual_total(monthly, 2026) is None


# --------------------------------------------------------------------------
# _compute_daily_stats
# --------------------------------------------------------------------------


def test_compute_daily_stats_cumulative() -> None:
    """Daily liters accumulate into a running sum."""
    daily = [
        {"date_releve": "2026-07-01", "consommation": {"litre": 100}},
        {"date_releve": "2026-07-02", "consommation": {"litre": 50}},
    ]
    stats = _compute_daily_stats(daily)
    assert len(stats) == 2
    assert stats[0] == {
        "start": datetime(2026, 7, 1, tzinfo=UTC),
        "state": 100,
        "sum": 100,
    }
    assert stats[1] == {
        "start": datetime(2026, 7, 2, tzinfo=UTC),
        "state": 50,
        "sum": 150,
    }


def test_compute_daily_stats_skips_invalid_dates() -> None:
    """Records with an unparsable date are ignored."""
    daily = [
        {"date_releve": "invalid", "consommation": {"litre": 100}},
        {"date_releve": "2026-07-02", "consommation": {"litre": 50}},
    ]
    stats = _compute_daily_stats(daily)
    assert len(stats) == 1
    assert stats[0]["state"] == 50


def test_compute_daily_stats_missing_consumption_defaults_zero() -> None:
    """A missing consommation dict defaults to zero liters."""
    daily = [{"date_releve": "2026-07-01"}]
    stats = _compute_daily_stats(daily)
    assert stats[0]["state"] == 0
    assert stats[0]["sum"] == 0


def test_compute_daily_stats_empty_list() -> None:
    """An empty list of records yields no rows."""
    assert _compute_daily_stats([]) == []


# --------------------------------------------------------------------------
# _compute_monthly_stats
# --------------------------------------------------------------------------


def test_compute_monthly_stats_cumulative() -> None:
    """Monthly m3 accumulate into a running sum."""
    monthly = [
        {"annee": 2026, "mois": 1, "consommation": {"m3": 1.0}},
        {"annee": 2026, "mois": 2, "consommation": {"m3": 2.0}},
    ]
    stats = _compute_monthly_stats(monthly)
    assert len(stats) == 2
    assert stats[0] == {
        "start": datetime(2026, 1, 1, tzinfo=UTC),
        "state": 1.0,
        "sum": 1.0,
    }
    assert stats[1] == {
        "start": datetime(2026, 2, 1, tzinfo=UTC),
        "state": 2.0,
        "sum": 3.0,
    }


def test_compute_monthly_stats_skips_missing_year_or_month() -> None:
    """Records missing year or month are skipped."""
    monthly = [
        {"mois": 1, "consommation": {"m3": 1.0}},
        {"annee": 2026, "consommation": {"m3": 1.0}},
    ]
    assert _compute_monthly_stats(monthly) == []


def test_compute_monthly_stats_skips_invalid_year_month() -> None:
    """Non-numeric year/month values are skipped rather than raising."""
    monthly = [{"annee": "bad", "mois": "bad", "consommation": {"m3": 1.0}}]
    assert _compute_monthly_stats(monthly) == []


def test_compute_monthly_stats_empty_list() -> None:
    """An empty list of records yields no rows."""
    assert _compute_monthly_stats([]) == []


# --------------------------------------------------------------------------
# _compute_index_stats (forward-fill)
# --------------------------------------------------------------------------


def test_compute_index_stats_forward_fills_gap_between_readings() -> None:
    """A gap between two readings is forward-filled with the previous state."""
    daily = [
        {"date_releve": "2026-07-01", "index": {"m3": 100.0}},
        {"date_releve": "2026-07-04", "index": {"m3": 103.0}},
    ]
    today = date(2026, 7, 4)
    stats = _compute_index_stats(daily, today)
    # 07-01 (real), 07-02 (filled), 07-03 (filled), 07-04 (real) = 4 rows.
    assert [row["start"].date() for row in stats] == [
        date(2026, 7, 1),
        date(2026, 7, 2),
        date(2026, 7, 3),
        date(2026, 7, 4),
    ]
    assert stats[1]["state"] == 100.0
    assert stats[2]["state"] == 100.0
    assert stats[3]["state"] == 103.0


def test_compute_index_stats_forward_fills_to_today() -> None:
    """After the last reading, the state is forward-filled up to today inclusive."""
    daily = [{"date_releve": "2026-07-01", "index": {"m3": 100.0}}]
    today = date(2026, 7, 3)
    stats = _compute_index_stats(daily, today)
    assert [row["start"].date() for row in stats] == [
        date(2026, 7, 1),
        date(2026, 7, 2),
        date(2026, 7, 3),
    ]
    assert all(row["state"] == 100.0 for row in stats)


def test_compute_index_stats_skips_invalid_date() -> None:
    """Records with an unparsable date are skipped entirely."""
    daily = [
        {"date_releve": "invalid-date", "index": {"m3": 999.0}},
        {"date_releve": "2026-07-02", "index": {"m3": 101.0}},
    ]
    today = date(2026, 7, 2)
    stats = _compute_index_stats(daily, today)
    assert len(stats) == 1
    assert stats[0]["state"] == 101.0


def test_compute_index_stats_skips_missing_index() -> None:
    """Records without a usable index value are skipped."""
    daily = [
        {"date_releve": "2026-07-01", "index": {}},
        {"date_releve": "2026-07-02", "index": {"m3": 101.0}},
    ]
    today = date(2026, 7, 2)
    stats = _compute_index_stats(daily, today)
    assert len(stats) == 1
    assert stats[0]["state"] == 101.0


def test_compute_index_stats_empty_daily_list() -> None:
    """No records yields no rows, even if today is far in the future."""
    assert _compute_index_stats([], date(2026, 7, 10)) == []


def test_compute_index_stats_no_fill_needed_when_today_is_last_reading() -> None:
    """No forward-fill rows are added when today matches the last reading."""
    daily = [{"date_releve": "2026-07-01", "index": {"m3": 100.0}}]
    stats = _compute_index_stats(daily, date(2026, 7, 1))
    assert len(stats) == 1


# --------------------------------------------------------------------------
# _compute_billing
# --------------------------------------------------------------------------


def test_compute_billing_waiting_and_future_selected() -> None:
    """WAITING and future items are candidates; the earliest one wins."""
    raw = build_account_data(
        solde=10.0,
        billing_plan={
            "prelevements_echeancier": [
                {"date": "2026-05-01", "montant": 40.0, "etat_prelevement": "DONE"},
                {"date": "2026-08-01", "montant": 50.0, "etat_prelevement": "WAITING"},
                {"date": "2026-09-01", "montant": 60.0, "etat_prelevement": "WAITING"},
            ]
        },
    )
    balance, monthly_payment, next_date, next_amount = _compute_billing(
        raw, date(2026, 7, 10)
    )
    assert balance == 10.0
    assert next_date == date(2026, 8, 1)
    assert next_amount == 50.0
    assert monthly_payment == 50.0


def test_compute_billing_past_non_waiting_excluded() -> None:
    """A past, non-WAITING item is not a valid upcoming payment."""
    raw = build_account_data(
        billing_plan={
            "prelevements_echeancier": [
                {"date": "2020-01-01", "montant": 30.0, "etat_prelevement": "DONE"},
            ]
        },
    )
    _balance, monthly_payment, next_date, next_amount = _compute_billing(
        raw, date(2026, 7, 10)
    )
    assert next_date is None
    assert next_amount is None
    # Falls back to the last known amount.
    assert monthly_payment == 30.0


def test_compute_billing_waiting_but_past_date_included() -> None:
    """A WAITING item is included even if its date is in the past."""
    raw = build_account_data(
        billing_plan={
            "prelevements_echeancier": [
                {"date": "2020-01-01", "montant": 30.0, "etat_prelevement": "WAITING"},
            ]
        },
    )
    _balance, _monthly_payment, next_date, next_amount = _compute_billing(
        raw, date(2026, 7, 10)
    )
    assert next_date == date(2020, 1, 1)
    assert next_amount == 30.0


def test_compute_billing_malformed_date_ignored() -> None:
    """An unparsable date is ignored for the upcoming selection but still recorded."""
    raw = build_account_data(
        billing_plan={
            "prelevements_echeancier": [
                {"date": "not-a-date", "montant": 20.0, "etat_prelevement": "WAITING"},
            ]
        },
    )
    _balance, monthly_payment, next_date, next_amount = _compute_billing(
        raw, date(2026, 7, 10)
    )
    assert next_date is None
    assert next_amount is None
    assert monthly_payment == 20.0


def test_compute_billing_no_billing_plan() -> None:
    """A missing billing plan yields no monthly payment or next payment."""
    raw = build_account_data(solde=5.0, billing_plan=None)
    balance, monthly_payment, next_date, next_amount = _compute_billing(
        raw, date(2026, 7, 10)
    )
    assert balance == 5.0
    assert monthly_payment is None
    assert next_date is None
    assert next_amount is None


def test_compute_billing_empty_schedule() -> None:
    """An empty schedule list yields no payment data."""
    raw = build_account_data(billing_plan={"prelevements_echeancier": []})
    _balance, monthly_payment, next_date, next_amount = _compute_billing(
        raw, date(2026, 7, 10)
    )
    assert monthly_payment is None
    assert next_date is None
    assert next_amount is None


def test_compute_billing_no_solde() -> None:
    """A missing/invalid solde attribute yields a None balance."""
    raw = build_account_data(solde=None)
    balance, *_ = _compute_billing(raw, date(2026, 7, 10))
    assert balance is None


def test_compute_billing_unexpected_shape_is_swallowed() -> None:
    """A completely malformed billing_plan does not raise."""
    raw = build_account_data(billing_plan="not-a-dict")
    balance, monthly_payment, next_date, next_amount = _compute_billing(
        raw, date(2026, 7, 10)
    )
    assert balance == raw.solde
    assert monthly_payment is None
    assert next_date is None
    assert next_amount is None


# --------------------------------------------------------------------------
# VeoliaModel.from_account_data
# --------------------------------------------------------------------------


def test_from_account_data_full() -> None:
    """The computed model exposes all derived fields from realistic data."""
    raw = build_account_data()
    today = date(2026, 7, 8)  # matches the last daily record.
    model = VeoliaModel.from_account_data(raw, today=today)

    computed = model.computed
    assert computed.last_index_m3 == pytest.approx(337.2)
    assert computed.last_daily_liters == 120
    assert computed.last_daily_m3 == pytest.approx(0.12)
    assert computed.monthly_latest_m3 == pytest.approx(3.4)
    assert computed.annual_total_m3 == pytest.approx(3.2 + 3.4)
    assert computed.last_date == date(2026, 7, 8)
    assert computed.daily_fiability == "MESURE"
    assert computed.monthly_fiability == "MESURE"
    assert len(computed.daily_stats_liters) == 3
    assert len(computed.monthly_stats_cubic_meters) == 3
    # Index stats forward-fill the 07-02 gap (07-01->07-03) and the
    # 07-04..07-07 gap (07-03->07-08): 3 real readings + 5 filled days.
    assert len(computed.index_stats_m3) == 8
    assert computed.daily_today_liters == 120
    assert computed.daily_today_m3 == pytest.approx(0.12)
    assert computed.daily_today_fiability == "MESURE"
    assert computed.balance == 12.5
    assert computed.next_payment_date == date(2026, 7, 15)
    assert computed.next_payment_amount == pytest.approx(45.0)
    assert computed.monthly_payment == pytest.approx(45.0)


def test_from_account_data_no_reading_today() -> None:
    """When today has no matching daily reading, the "today" fields are None."""
    raw = build_account_data()
    model = VeoliaModel.from_account_data(raw, today=date(2026, 7, 20))
    assert model.computed.daily_today_liters is None
    assert model.computed.daily_today_m3 is None
    assert model.computed.daily_today_fiability is None


def test_from_account_data_empty_consumption_lists() -> None:
    """Empty consumption lists degrade gracefully to None/zero values."""
    raw = build_account_data(daily_consumption=[], monthly_consumption=[])
    model = VeoliaModel.from_account_data(raw, today=date(2026, 7, 8))
    computed = model.computed
    assert computed.last_index_m3 is None
    assert computed.last_daily_liters is None
    assert computed.last_daily_m3 is None
    assert computed.monthly_latest_m3 is None
    assert computed.annual_total_m3 == 0.0
    assert computed.last_date is None
    assert computed.daily_stats_liters == []
    assert computed.monthly_stats_cubic_meters == []
    assert computed.index_stats_m3 == []
    assert computed.daily_today_liters is None


def test_from_account_data_none_consumption_lists() -> None:
    """None consumption lists (never fetched yet) also degrade gracefully."""
    raw = build_account_data(daily_consumption=None, monthly_consumption=None)
    model = VeoliaModel.from_account_data(raw, today=date(2026, 7, 8))
    assert model.computed.last_index_m3 is None
    assert model.computed.daily_stats_liters == []


def test_veolia_model_proxies_unknown_attributes_to_raw() -> None:
    """Attribute access falls through to the raw account data."""
    raw = build_account_data()
    model = VeoliaModel.from_account_data(raw, today=date(2026, 7, 8))
    assert model.numero_compteur == raw.numero_compteur
    assert model.id_abonnement == raw.id_abonnement
    assert model.alert_settings is raw.alert_settings


def test_veolia_model_proxy_raises_for_truly_unknown_attribute() -> None:
    """An attribute that doesn't exist anywhere raises AttributeError."""
    raw = build_account_data()
    model = VeoliaModel.from_account_data(raw, today=date(2026, 7, 8))
    with pytest.raises(AttributeError):
        _ = model.this_attribute_does_not_exist
