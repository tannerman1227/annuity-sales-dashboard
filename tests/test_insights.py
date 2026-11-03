"""Written observations stay specific and stay quiet on an empty view."""

import pandas as pd

from src.insights import build_insights


def _frame(rows):
    return pd.DataFrame(rows)


def test_empty_view_is_a_single_sentence():
    lines = build_insights(
        premium=0,
        policies=0,
        period_growth=None,
        prior_premium=None,
        period_start_text="Jan 1, 2026",
        period_end_text="Oct 31, 2026",
        ytd_growth=None,
        ytd_label="2026 YTD through Oct 31, 2026",
        products=pd.DataFrame(),
        channels=pd.DataFrame(),
        regions=pd.DataFrame(),
        top10_share=None,
    )
    assert len(lines) == 1
    assert "No issued premium" in lines[0]


def test_insights_name_the_leader_and_the_growth():
    products = _frame(
        [
            {"product": "Fixed Indexed", "premium": 500, "share": 0.50, "prior_share": 0.40},
            {"product": "MYGA", "premium": 300, "share": 0.30, "prior_share": 0.35},
        ]
    )
    channels = _frame(
        [{"channel": "Independent Agents", "premium": 700, "share": 0.70}]
    )
    regions = _frame([{"region": "South", "premium": 400, "share": 0.40}])
    lines = build_insights(
        premium=1_000_000,
        policies=8,
        period_growth=0.084,
        prior_premium=920_000,
        period_start_text="Jan 1, 2026",
        period_end_text="Oct 31, 2026",
        ytd_growth=0.084,
        ytd_label="2026 YTD through Oct 31, 2026",
        products=products,
        channels=channels,
        regions=regions,
        top10_share=0.36,
    )
    assert len(lines) == 3
    assert "8 policies" in lines[0]
    assert "+8.4%" in lines[0]
    assert "Fixed Indexed" in lines[1]
    assert "10.0 points higher" in lines[1]
    assert "Independent Agents" in lines[2]
    assert "South" in lines[2]
    assert "36.0%" in lines[2]


def test_unmatched_window_points_at_ytd_growth():
    products = _frame([{"product": "MYGA", "premium": 100, "share": 1.0}])
    lines = build_insights(
        premium=2_000_000_000,
        policies=100,
        period_growth=None,
        prior_premium=None,
        period_start_text="Jan 1, 2022",
        period_end_text="Oct 31, 2026",
        ytd_growth=0.05,
        ytd_label="2026 YTD through Oct 31, 2026",
        products=products,
        channels=pd.DataFrame(),
        regions=pd.DataFrame(),
        top10_share=None,
    )
    assert "period growth is omitted" in lines[0]
    assert "+5.0%" in lines[0]
    assert "MYGA" in lines[1]
