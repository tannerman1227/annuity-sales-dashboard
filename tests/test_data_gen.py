"""The seeded book validates, repeats, and has a recognizable annuity shape."""

from pathlib import Path

import pandas as pd

from src.constants import SEED
from src.data_gen import generate_sales
from src.validation import validate_sales

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "annuity_sales.csv"


def test_generator_is_deterministic_and_valid():
    first = generate_sales(seed=SEED)
    second = generate_sales(seed=SEED)
    pd.testing.assert_frame_equal(first, second)
    result = validate_sales(first)
    assert result.ok, result.issues
    assert 20_000 < len(first) < 45_000
    assert first["issue_date"].min() == pd.Timestamp("2022-01-01") or first["issue_date"].min() >= pd.Timestamp("2022-01-01")
    assert first["issue_date"].max() <= pd.Timestamp("2026-10-31")
    assert first["issue_date"].max() >= pd.Timestamp("2026-10-01")


def test_recent_mix_matches_the_product_story():
    sales = generate_sales(seed=SEED)
    recent = sales[sales["issue_date"] >= "2025-01-01"]
    premium = recent.groupby("product")["premium"].sum()
    assert premium.idxmax() == "Fixed Indexed"

    variable = recent[recent["product"] == "Variable"]
    assert (variable["channel"] == "Broker-Dealers").mean() > 0.6

    myga = recent[recent["product"] == "MYGA"]
    assert (myga["channel"] == "Banks").mean() > 0.4

    indexed = recent[recent["product"] == "Fixed Indexed"]
    assert (indexed["channel"] == "Independent Agents").mean() > 0.5


def test_shipped_csv_matches_the_generator():
    assert CSV_PATH.exists(), "Run python -m src.data_gen before the tests."
    shipped = pd.read_csv(CSV_PATH)
    fresh = generate_sales(seed=SEED)
    shipped["issue_date"] = pd.to_datetime(shipped["issue_date"])
    shipped["premium"] = shipped["premium"].round(2)
    shipped["guarantee_years"] = shipped["guarantee_years"].astype(int)
    fresh["premium"] = fresh["premium"].round(2)
    pd.testing.assert_frame_equal(
        shipped[list(fresh.columns)].reset_index(drop=True),
        fresh.reset_index(drop=True),
        check_dtype=False,
    )
