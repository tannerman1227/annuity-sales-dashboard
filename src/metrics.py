"""Pure sales metrics. The Streamlit app and the tests both call these."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from src.constants import MONTH_ABBR, STATE_TO_REGION, STATE_WEIGHTS


def apply_filters(
    df: pd.DataFrame,
    start,
    end,
    products: Sequence[str] | None = None,
    channels: Sequence[str] | None = None,
    states: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Inclusive issue-date window, then optional product, channel, and state lists.

    None means "no restriction". An empty sequence restricts to nothing.
    """
    start_ts = pd.Timestamp(start).normalize()
    end_ts = pd.Timestamp(end).normalize()
    mask = (df["issue_date"] >= start_ts) & (df["issue_date"] <= end_ts)
    if products is not None:
        mask = mask & df["product"].isin(list(products))
    if channels is not None:
        mask = mask & df["channel"].isin(list(channels))
    if states is not None:
        mask = mask & df["state"].isin(list(states))
    return df.loc[mask].copy()


def total_premium(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    return float(df["premium"].sum())


def policy_count(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    return int(df["policy_id"].nunique())


def average_premium(df: pd.DataFrame) -> float | None:
    count = policy_count(df)
    if count == 0:
        return None
    return total_premium(df) / count


def growth_rate(current: float | None, prior: float | None) -> float | None:
    """Relative change. Undefined when the prior base is missing or zero."""
    if current is None or prior is None:
        return None
    if not np.isfinite(current) or not np.isfinite(prior) or prior == 0:
        return None
    return float((current - prior) / prior)


def shift_years(start, end, years: int = 1) -> tuple[pd.Timestamp, pd.Timestamp]:
    start_ts = pd.Timestamp(start).normalize()
    end_ts = pd.Timestamp(end).normalize()
    return start_ts - pd.DateOffset(years=years), end_ts - pd.DateOffset(years=years)


def ytd_bounds(as_of) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Calendar year-to-date through `as_of`, including January even if a filter starts later."""
    as_of_ts = pd.Timestamp(as_of).normalize()
    return pd.Timestamp(as_of_ts.year, 1, 1), as_of_ts


def resolve_window(
    preset: str,
    data_min,
    data_max,
    custom_start=None,
    custom_end=None,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Turn a sidebar preset into an inclusive issue-date window inside the book."""
    data_min_ts = pd.Timestamp(data_min).normalize()
    data_max_ts = pd.Timestamp(data_max).normalize()
    if preset == "ytd":
        start = pd.Timestamp(data_max_ts.year, 1, 1)
        end = data_max_ts
    elif preset == "last_12":
        start = (data_max_ts.replace(day=1) - pd.DateOffset(months=11)).normalize()
        end = data_max_ts
    elif preset == "since_2024":
        start = pd.Timestamp(2024, 1, 1)
        end = data_max_ts
    elif preset == "custom":
        if custom_start is None or custom_end is None:
            start, end = data_min_ts, data_max_ts
        else:
            start = pd.Timestamp(custom_start).normalize()
            end = pd.Timestamp(custom_end).normalize()
    else:
        start, end = data_min_ts, data_max_ts
    start = max(start, data_min_ts)
    end = min(end, data_max_ts)
    if start > end:
        start, end = end, start
    return start, end


def prior_window_supported(prior_start, data_min) -> bool:
    return pd.Timestamp(prior_start).normalize() >= pd.Timestamp(data_min).normalize()


def monthly_frame(df: pd.DataFrame) -> pd.DataFrame:
    """One row per month from the first issue month through the last, gaps filled with zero."""
    columns = ["month", "premium", "policies"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    grouped = (
        df.groupby(df["issue_date"].dt.to_period("M"))
        .agg(premium=("premium", "sum"), policies=("policy_id", "nunique"))
        .sort_index()
    )
    grouped.index = grouped.index.to_timestamp()
    full = pd.date_range(grouped.index.min(), grouped.index.max(), freq="MS")
    grouped = grouped.reindex(full)
    grouped["premium"] = grouped["premium"].fillna(0.0)
    grouped["policies"] = grouped["policies"].fillna(0).astype(int)
    grouped.index.name = "month"
    return grouped.reset_index()


def attach_growth(plotted: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    """Add month-over-month and year-over-year premium growth to a plotted monthly frame.

    Year-over-year looks up the same month in `history`, which may extend outside
    the plotted window. That is what lets a 2026 view compare against 2025.
    """
    out = plotted.copy()
    if out.empty:
        out["mom_pct"] = pd.Series(dtype=float)
        out["yoy_pct"] = pd.Series(dtype=float)
        return out
    out["mom_pct"] = out["premium"].pct_change().replace([np.inf, -np.inf], np.nan)
    if history.empty:
        out["yoy_pct"] = np.nan
        return out
    lookup = history.copy()
    lookup["key"] = pd.to_datetime(lookup["month"]).dt.to_period("M")
    lookup = lookup.drop_duplicates("key").set_index("key")["premium"]
    prior_keys = pd.to_datetime(out["month"]).dt.to_period("M") - 12
    base_values = pd.to_numeric(prior_keys.map(lookup), errors="coerce").to_numpy(dtype=float)
    premiums = out["premium"].to_numpy(dtype=float)
    yoy = np.full(len(out), np.nan)
    valid = np.isfinite(base_values) & (base_values != 0) & np.isfinite(premiums)
    yoy[valid] = premiums[valid] / base_values[valid] - 1.0
    out["yoy_pct"] = yoy
    return out


def breakdown(
    current: pd.DataFrame,
    column: str,
    prior: pd.DataFrame | None = None,
    order: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Premium, policy count, average, share, and optional prior-year comparison."""
    if current.empty:
        grouped = pd.DataFrame(columns=[column, "premium", "policies"])
    else:
        grouped = (
            current.groupby(column, dropna=False)
            .agg(premium=("premium", "sum"), policies=("policy_id", "nunique"))
            .reset_index()
        )
    if order is not None:
        skeleton = pd.DataFrame({column: list(order)})
        grouped = skeleton.merge(grouped, on=column, how="left")
    grouped["premium"] = grouped["premium"].fillna(0.0) if "premium" in grouped else 0.0
    grouped["policies"] = grouped["policies"].fillna(0).astype(int) if "policies" in grouped else 0
    total = float(grouped["premium"].sum()) if not grouped.empty else 0.0
    if total > 0:
        grouped["share"] = grouped["premium"] / total
    else:
        grouped["share"] = np.nan
    grouped["avg_premium"] = np.nan
    if not grouped.empty:
        positive_policies = grouped["policies"] > 0
        grouped.loc[positive_policies, "avg_premium"] = (
            grouped.loc[positive_policies, "premium"] / grouped.loc[positive_policies, "policies"]
        )

    if prior is not None:
        if prior.empty:
            prior_premium = pd.Series(0.0, index=grouped[column])
        else:
            prior_premium = prior.groupby(column)["premium"].sum()
        grouped["prior_premium"] = grouped[column].map(prior_premium).fillna(0.0)
        prior_total = float(grouped["prior_premium"].sum()) if not prior.empty else 0.0
        # Prior share uses the prior book's own total, not the sum after reindexing
        # to categories that only exist in the current window.
        if not prior.empty:
            prior_total = float(prior["premium"].sum())
        grouped["prior_share"] = np.where(
            prior_total > 0, grouped["prior_premium"] / prior_total, np.nan
        )
        grouped["premium_growth"] = growth_series(grouped["premium"], grouped["prior_premium"])

    grouped = grouped[grouped["premium"] > 0].reset_index(drop=True)
    if order is not None:
        rank = {value: index for index, value in enumerate(order)}
        grouped["_order"] = grouped[column].map(rank)
        grouped = grouped.sort_values("_order").drop(columns="_order")
    else:
        grouped = grouped.sort_values(["premium", column], ascending=[False, True])
    return grouped.reset_index(drop=True)


def growth_series(current: pd.Series, prior: pd.Series) -> pd.Series:
    current_values = current.astype(float)
    prior_values = prior.astype(float)
    result = (current_values - prior_values) / prior_values.replace(0, np.nan)
    return result.replace([np.inf, -np.inf], np.nan)


def cumulative_ytd(df: pd.DataFrame, as_of, data_start) -> pd.DataFrame:
    """Month-aligned cumulative premium for the as-of year and the year before it.

    The prior year is omitted when it starts before the dataset, so a missing
    history year is not drawn as if it were a year of zero sales.
    """
    columns = ["role", "year", "month", "month_label", "monthly_premium", "cumulative_premium"]
    as_of_ts = pd.Timestamp(as_of).normalize()
    first_year = pd.Timestamp(data_start).year
    frames: list[pd.DataFrame] = []
    for offset, role in ((0, "current"), (1, "prior")):
        end = (as_of_ts - pd.DateOffset(years=offset)).normalize()
        if end.year < first_year:
            continue
        start = pd.Timestamp(end.year, 1, 1)
        window = df[(df["issue_date"] >= start) & (df["issue_date"] <= end)]
        if window.empty:
            monthly = pd.Series(0.0, index=range(1, end.month + 1))
        else:
            monthly = (
                window.groupby(window["issue_date"].dt.month)["premium"]
                .sum()
                .reindex(range(1, end.month + 1), fill_value=0.0)
            )
        frames.append(
            pd.DataFrame(
                {
                    "role": role,
                    "year": end.year,
                    "month": monthly.index.astype(int),
                    "month_label": [MONTH_ABBR[month - 1] for month in monthly.index],
                    "monthly_premium": monthly.to_numpy(dtype=float),
                    "cumulative_premium": monthly.cumsum().to_numpy(dtype=float),
                }
            )
        )
    if not frames:
        return pd.DataFrame(columns=columns)
    return pd.concat(frames, ignore_index=True)


def top_distributors(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    columns = [
        "distributor_id",
        "distributor_name",
        "channel",
        "premium",
        "policies",
        "avg_premium",
        "share",
    ]
    if df.empty or total_premium(df) <= 0:
        return pd.DataFrame(columns=columns)
    grouped = (
        df.groupby(["distributor_id", "distributor_name", "channel"], as_index=False)
        .agg(premium=("premium", "sum"), policies=("policy_id", "nunique"))
        .sort_values(["premium", "distributor_name"], ascending=[False, True])
    )
    grouped["avg_premium"] = grouped["premium"] / grouped["policies"]
    grouped["share"] = grouped["premium"] / grouped["premium"].sum()
    return grouped.head(n).reset_index(drop=True)


def concentration(df: pd.DataFrame, n: int = 10) -> float | None:
    """Share of premium held by the n largest distributors."""
    if df.empty or total_premium(df) <= 0:
        return None
    ranked = df.groupby("distributor_id")["premium"].sum().sort_values(ascending=False)
    return float(ranked.head(n).sum() / ranked.sum())


def state_rollup(df: pd.DataFrame) -> pd.DataFrame:
    """Premium by state for every jurisdiction, including those with no sales."""
    base = pd.DataFrame(
        {
            "state": list(STATE_WEIGHTS),
            "region": [STATE_TO_REGION[state] for state in STATE_WEIGHTS],
        }
    )
    if df.empty:
        base["premium"] = 0.0
        base["policies"] = 0
    else:
        aggregated = df.groupby("state").agg(
            premium=("premium", "sum"), policies=("policy_id", "nunique")
        )
        base = base.merge(aggregated, left_on="state", right_index=True, how="left")
        base["premium"] = base["premium"].fillna(0.0)
        base["policies"] = base["policies"].fillna(0).astype(int)
    total = float(base["premium"].sum())
    base["share"] = np.where(total > 0, base["premium"] / total, 0.0)
    base["avg_premium"] = np.where(base["policies"] > 0, base["premium"] / base["policies"], np.nan)
    return base.sort_values(["premium", "state"], ascending=[False, True]).reset_index(drop=True)


def product_channel(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["product", "channel", "premium", "policies"])
    grouped = (
        df.groupby(["product", "channel"], as_index=False)
        .agg(premium=("premium", "sum"), policies=("policy_id", "nunique"))
        .sort_values("premium", ascending=False)
    )
    return grouped.reset_index(drop=True)


def training_series(df: pd.DataFrame, as_of) -> tuple[pd.Series, str]:
    """Monthly premium through `as_of` for the forecast.

    A trailing month that the window does not cover through month-end is dropped
    so a partial month does not pull the projected level down.
    """
    as_of_ts = pd.Timestamp(as_of).normalize()
    history = df[df["issue_date"] <= as_of_ts]
    frame = monthly_frame(history)
    if frame.empty:
        return pd.Series(dtype=float, name="premium"), "No issued premium is available to fit an outlook."
    series = frame.set_index("month")["premium"].astype(float)
    last_month = pd.Timestamp(series.index.max())
    month_end = (last_month + pd.offsets.MonthEnd(0)).normalize()
    if as_of_ts < month_end:
        kept = series.iloc[:-1]
        note = (
            f"{last_month.strftime('%B %Y')} is partial "
            f"(the window ends {as_of_ts.strftime('%b')} {as_of_ts.day}, {as_of_ts.year}), "
            "so the outlook is trained through the prior complete month."
        )
        if kept.empty:
            return series, note
        return kept, note
    return series, ""
