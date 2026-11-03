"""Short written read of the filtered book. Deterministic, no model calls."""

from __future__ import annotations

import pandas as pd

from src.formatting import format_pct, format_premium


def _sentence(clauses: list[str]) -> str:
    cleaned = [clause.strip().rstrip(".") for clause in clauses if clause and clause.strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        text = cleaned[0]
    elif len(cleaned) == 2:
        text = f"{cleaned[0]}, and {cleaned[1]}"
    else:
        text = ", ".join(cleaned[:-1]) + f", and {cleaned[-1]}"
    return text[0].upper() + text[1:] + "."


def build_insights(
    *,
    premium: float,
    policies: int,
    period_growth: float | None,
    prior_premium: float | None,
    period_start_text: str,
    period_end_text: str,
    ytd_growth: float | None,
    ytd_label: str,
    products: pd.DataFrame,
    channels: pd.DataFrame,
    regions: pd.DataFrame,
    top10_share: float | None,
) -> list[str]:
    """Three observations for the current filters. One observation when the view is empty."""
    if policies == 0 or premium <= 0:
        return [
            "No issued premium matches these filters. Widen the dates or clear a product, channel, or state."
        ]

    if period_growth is None:
        if ytd_growth is None:
            period_line = (
                f"Between {period_start_text} and {period_end_text}, issued premium is "
                f"{format_premium(premium)} across {policies:,} policies. "
                "A matched prior-year window is not in this dataset, so period growth is omitted."
            )
        else:
            period_line = (
                f"Between {period_start_text} and {period_end_text}, issued premium is "
                f"{format_premium(premium)} across {policies:,} policies. "
                "The matched prior-year window starts before this book, so period growth is omitted. "
                f"{ytd_label} growth is {format_pct(ytd_growth)}."
            )
    else:
        prior_text = f" ({format_premium(prior_premium)})" if prior_premium is not None else ""
        period_line = (
            f"Between {period_start_text} and {period_end_text}, issued premium is "
            f"{format_premium(premium)} across {policies:,} policies, "
            f"{format_pct(period_growth)} versus the same dates a year earlier{prior_text}."
        )

    product_line = "No product mix is available in this view."
    if not products.empty and "share" in products.columns:
        ranked = products.sort_values("premium", ascending=False)
        leader = ranked.iloc[0]
        product_line = (
            f"{leader['product']} leads this view with {leader['share']:.1%} of premium "
            f"({format_premium(leader['premium'])})."
        )
        prior_share = leader["prior_share"] if "prior_share" in ranked.columns else None
        if prior_share is not None and pd.notna(prior_share) and pd.notna(leader["share"]):
            points = (float(leader["share"]) - float(prior_share)) * 100
            if abs(points) >= 0.1:
                direction = "higher" if points > 0 else "lower"
                product_line = product_line[:-1] + (
                    f", {abs(points):.1f} points {direction} than its share in the prior-year window."
                )

    clauses: list[str] = []
    if not channels.empty and channels["premium"].sum() > 0:
        channel = channels.sort_values("premium", ascending=False).iloc[0]
        clauses.append(f"most premium runs through {channel['channel']} ({channel['share']:.1%})")
    if not regions.empty and regions["premium"].sum() > 0:
        region = regions.sort_values("premium", ascending=False).iloc[0]
        clauses.append(f"the largest region is the {region['region']} ({region['share']:.1%})")
    if top10_share is not None:
        clauses.append(f"the top 10 distributors hold {top10_share:.1%}")
    mix_line = _sentence(clauses) if clauses else "Channel and region mix are unavailable in this view."
    return [period_line, product_line, mix_line]
