"""Charts build from a tiny frame and survive an empty one."""

import pandas as pd
import plotly.graph_objects as go

from src.charts import (
    chart_cumulative_ytd,
    chart_distributors,
    chart_forecast,
    chart_map,
    chart_mom,
    chart_monthly,
    chart_product_channel,
    chart_product_mix,
    chart_profile,
)
from src.forecast import forecast_monthly_premium
from src.metrics import breakdown, cumulative_ytd, monthly_frame, state_rollup, top_distributors


def sample() -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "policy_id": ["POL-1", "POL-2", "POL-3"],
            "issue_date": pd.to_datetime(["2026-01-10", "2026-02-10", "2025-01-10"]),
            "product": ["Fixed Indexed", "MYGA", "Fixed Indexed"],
            "channel": ["Independent Agents", "Banks", "Independent Agents"],
            "state": ["TX", "CA", "TX"],
            "region": ["South", "West", "South"],
            "distributor_id": ["DST-1", "DST-2", "DST-1"],
            "distributor_name": ["Summit Peak IMO", "First Meridian Bank", "Summit Peak IMO"],
            "premium": [100_000, 80_000, 90_000],
            "annuitant_age_band": ["65-69", "70-74", "65-69"],
            "tax_status": ["Qualified", "Non-qualified", "Qualified"],
            "guarantee_years": [7, 5, 7],
        }
    )
    return frame


def test_charts_return_figures():
    frame = sample()
    monthly = monthly_frame(frame)
    monthly["mom_pct"] = monthly["premium"].pct_change()
    monthly["yoy_pct"] = monthly["premium"] * 0 + 0.05
    figures = [
        chart_cumulative_ytd(cumulative_ytd(frame, "2026-02-28", "2022-01-01")),
        chart_monthly(monthly),
        chart_mom(monthly),
        chart_product_mix(breakdown(frame, "product")),
        chart_profile(breakdown(frame, "channel"), "channel", "By channel"),
        chart_product_channel(frame.groupby(["product", "channel"], as_index=False)["premium"].sum()),
        chart_map(state_rollup(frame)),
        chart_distributors(top_distributors(frame, n=5)),
        chart_forecast(monthly.set_index("month")["premium"], forecast_monthly_premium(monthly.set_index("month")["premium"]).forecast),
    ]
    assert all(isinstance(fig, go.Figure) and len(fig.data) > 0 for fig in figures)


def test_monthly_yoy_axis_stays_a_percent():
    frame = sample()
    monthly = monthly_frame(frame)
    monthly["mom_pct"] = monthly["premium"].pct_change()
    monthly["yoy_pct"] = [0.05] * len(monthly)
    fig = chart_monthly(monthly)
    assert fig.layout.yaxis.tickformat == "$.3s"
    assert fig.layout.yaxis2.tickformat == "+.0%"
    assert fig.data[1].yaxis == "y2"


def test_empty_charts_do_not_raise():
    empty = sample().iloc[0:0]
    monthly = monthly_frame(empty)
    figures = [
        chart_product_mix(breakdown(empty, "product")),
        chart_map(state_rollup(empty)),
        chart_distributors(top_distributors(empty)),
        chart_monthly(monthly),
        chart_forecast(pd.Series(dtype=float), pd.DataFrame(columns=["month", "forecast", "lower", "upper"])),
    ]
    assert all(isinstance(fig, go.Figure) for fig in figures)
