"""Metric calculations on small, hand-built books."""

from datetime import date

import pandas as pd
import pytest

from src.metrics import (
    apply_filters,
    attach_growth,
    average_premium,
    breakdown,
    concentration,
    cumulative_ytd,
    growth_rate,
    monthly_frame,
    policy_count,
    prior_window_supported,
    resolve_window,
    shift_years,
    state_rollup,
    top_distributors,
    total_premium,
    training_series,
    ytd_bounds,
)


def book() -> pd.DataFrame:
    rows = [
        ("POL-1", "2025-01-15", "Fixed", "Banks", "TX", "South", "DST-1", "Alpha Bank", "AGT-1", 100_000),
        ("POL-2", "2025-01-20", "MYGA", "Banks", "TX", "South", "DST-1", "Alpha Bank", "AGT-1", 50_000),
        ("POL-3", "2025-03-01", "Fixed", "Banks", "CA", "West", "DST-1", "Alpha Bank", "AGT-2", 40_000),
        ("POL-4", "2026-01-10", "Fixed", "Banks", "CA", "West", "DST-1", "Alpha Bank", "AGT-2", 80_000),
        ("POL-5", "2026-01-18", "Fixed Indexed", "Independent Agents", "FL", "South", "DST-2", "Summit", "AGT-3", 120_000),
        ("POL-6", "2026-02-02", "Variable", "Broker-Dealers", "NY", "Northeast", "DST-3", "Northstar", "AGT-4", 200_000),
        ("POL-7", "2026-10-15", "MYGA", "Banks", "TX", "South", "DST-1", "Alpha Bank", "AGT-1", 60_000),
    ]
    frame = pd.DataFrame(
        rows,
        columns=[
            "policy_id",
            "issue_date",
            "product",
            "channel",
            "state",
            "region",
            "distributor_id",
            "distributor_name",
            "writing_agent_id",
            "premium",
        ],
    )
    frame["issue_date"] = pd.to_datetime(frame["issue_date"])
    return frame


def test_totals_and_average():
    frame = book()
    assert total_premium(frame) == pytest.approx(650_000)
    assert policy_count(frame) == 7
    assert average_premium(frame) == pytest.approx(650_000 / 7)
    assert average_premium(frame.iloc[0:0]) is None
    assert policy_count(frame.iloc[0:0]) == 0
    assert total_premium(frame.iloc[0:0]) == 0


def test_growth_rate_edges():
    assert growth_rate(110, 100) == pytest.approx(0.10)
    assert growth_rate(90, 100) == pytest.approx(-0.10)
    assert growth_rate(100, 0) is None
    assert growth_rate(100, None) is None
    assert growth_rate(None, 100) is None


def test_filters_are_inclusive_and_combine():
    frame = book()
    window = apply_filters(
        frame,
        "2026-01-01",
        "2026-01-31",
        products=["Fixed"],
        channels=["Banks"],
        states=["CA"],
    )
    assert list(window["policy_id"]) == ["POL-4"]
    assert apply_filters(frame, "2026-01-10", "2026-01-10").shape[0] == 1
    assert apply_filters(frame, "2026-01-01", "2026-12-31", products=[]).empty
    assert apply_filters(frame, "2026-01-01", "2026-12-31", products=None).shape[0] == 4


def test_ytd_bounds_and_supported_prior_window():
    start, end = ytd_bounds("2026-10-31")
    assert start == pd.Timestamp("2026-01-01")
    assert end == pd.Timestamp("2026-10-31")
    prior_start, prior_end = shift_years(start, end)
    assert prior_start == pd.Timestamp("2025-01-01")
    assert prior_end == pd.Timestamp("2025-10-31")
    assert prior_window_supported(prior_start, "2022-01-01")
    assert not prior_window_supported("2021-01-01", "2022-01-01")


def test_resolve_window_presets():
    data_min = date(2022, 1, 1)
    data_max = date(2026, 10, 31)
    start, end = resolve_window("ytd", data_min, data_max)
    assert (start, end) == (pd.Timestamp("2026-01-01"), pd.Timestamp("2026-10-31"))
    start, end = resolve_window("last_12", data_min, data_max)
    assert (start, end) == (pd.Timestamp("2025-11-01"), pd.Timestamp("2026-10-31"))
    start, end = resolve_window("since_2024", data_min, data_max)
    assert start == pd.Timestamp("2024-01-01")
    start, end = resolve_window("full", data_min, data_max)
    assert start == pd.Timestamp("2022-01-01") and end == pd.Timestamp("2026-10-31")
    start, end = resolve_window("custom", data_min, data_max, "2026-05-01", "2026-01-01")
    assert start == pd.Timestamp("2026-01-01")
    assert end == pd.Timestamp("2026-05-01")


def test_monthly_frame_fills_gaps_and_yoy_looks_outside_the_plot():
    frame = book()
    current = apply_filters(frame, "2026-01-01", "2026-03-31")
    plotted = monthly_frame(current)
    assert list(plotted["month"].dt.strftime("%Y-%m")) == ["2026-01", "2026-02"]
    grown = attach_growth(plotted, monthly_frame(frame))
    january = grown.loc[grown["month"] == "2026-01-01"].iloc[0]
    assert january["premium"] == pytest.approx(200_000)
    assert january["yoy_pct"] == pytest.approx(200_000 / 150_000 - 1)
    february = grown.loc[grown["month"] == "2026-02-01"].iloc[0]
    assert pd.isna(february["yoy_pct"])
    assert pd.isna(grown.iloc[0]["mom_pct"])
    assert grown.iloc[1]["mom_pct"] == pytest.approx(0.0)

    gapped = pd.DataFrame(
        {
            "policy_id": ["A", "B"],
            "issue_date": pd.to_datetime(["2026-01-15", "2026-03-15"]),
            "premium": [10.0, 30.0],
        }
    )
    filled = monthly_frame(gapped)
    assert list(filled["month"].dt.month) == [1, 2, 3]
    assert filled.loc[filled["month"] == "2026-02-01", "premium"].item() == 0
    assert filled.loc[filled["month"] == "2026-02-01", "policies"].item() == 0


def test_breakdown_shares_and_growth():
    frame = book()
    current = apply_filters(frame, "2026-01-01", "2026-12-31")
    prior = apply_filters(frame, "2025-01-01", "2025-12-31")
    products = breakdown(current, "product", prior, ["Fixed", "Fixed Indexed", "Variable", "MYGA"])
    assert products["share"].sum() == pytest.approx(1)
    fixed = products.loc[products["product"] == "Fixed"].iloc[0]
    assert fixed["premium"] == pytest.approx(80_000)
    assert fixed["prior_premium"] == pytest.approx(140_000)
    assert fixed["premium_growth"] == pytest.approx(80_000 / 140_000 - 1)
    assert "MYGA" not in set(products["product"]) or products.loc[products["product"] == "MYGA", "premium"].item() == 60_000


def test_cumulative_ytd_aligns_years_and_skips_missing_history():
    frame = book()
    curve = cumulative_ytd(frame, "2026-02-28", "2022-01-01")
    current = curve[curve["role"] == "current"]
    prior = curve[curve["role"] == "prior"]
    assert list(current["month_label"]) == ["Jan", "Feb"]
    assert current["cumulative_premium"].tolist() == pytest.approx([200_000, 400_000])
    assert prior["cumulative_premium"].tolist() == pytest.approx([150_000, 150_000])
    early = cumulative_ytd(frame, "2022-06-30", "2022-01-01")
    assert set(early["role"]) == {"current"}


def test_top_distributors_and_concentration():
    frame = book()
    ranking = top_distributors(frame, n=2)
    assert list(ranking["distributor_name"]) == ["Alpha Bank", "Northstar"]
    assert ranking.iloc[0]["premium"] == pytest.approx(330_000)
    assert ranking.iloc[0]["share"] == pytest.approx(330_000 / 650_000)
    assert concentration(frame, n=1) == pytest.approx(330_000 / 650_000)
    assert concentration(frame.iloc[0:0], n=10) is None


def test_state_rollup_keeps_every_jurisdiction():
    rolled = state_rollup(book())
    assert len(rolled) == 51
    assert rolled["share"].sum() == pytest.approx(1)
    texas = rolled.loc[rolled["state"] == "TX"].iloc[0]
    assert texas["premium"] == pytest.approx(210_000)
    assert texas["region"] == "South"
    assert rolled.loc[rolled["state"] == "WY", "premium"].item() == 0


def test_training_series_drops_partial_final_month():
    frame = book()
    series, note = training_series(frame, "2026-10-15")
    assert series.index.max() == pd.Timestamp("2026-09-01")
    assert "partial" in note
    complete, note = training_series(frame, "2026-10-31")
    assert complete.index.max() == pd.Timestamp("2026-10-01")
    assert note == ""
    assert complete.loc[pd.Timestamp("2026-01-01")] == pytest.approx(200_000)
