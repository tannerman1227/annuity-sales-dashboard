"""Range, schema, and referential checks for the sales book."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.constants import (
    AGE_BANDS,
    CHANNELS,
    DATA_END,
    DATA_START,
    DISTRIBUTORS,
    GUARANTEE_YEARS,
    MAX_PREMIUM,
    MIN_PREMIUM,
    PRODUCTS,
    REQUIRED_COLUMNS,
    STATE_TO_REGION,
    TAX_STATUSES,
    build_agent_roster,
)


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    row_count: int
    issues: tuple[str, ...]


def validate_sales(df: pd.DataFrame) -> ValidationResult:
    """Return every problem found. An empty issue list means the frame is usable."""
    issues: list[str] = []
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        issues.append("Missing columns: " + ", ".join(missing))
        return ValidationResult(False, int(len(df)), tuple(issues))

    row_count = int(len(df))
    if row_count == 0:
        issues.append("Dataset has no rows.")
        return ValidationResult(False, 0, tuple(issues))

    for column in REQUIRED_COLUMNS:
        if df[column].isna().any():
            issues.append(f"Missing values in {column}.")

    if df["policy_id"].duplicated().any():
        dupes = int(df["policy_id"].duplicated().sum())
        issues.append(f"{dupes} duplicate policy_id values.")

    issue_dates = pd.to_datetime(df["issue_date"], errors="coerce")
    if issue_dates.isna().any():
        issues.append("Unparseable issue_date values.")
    else:
        start = pd.Timestamp(DATA_START)
        end = pd.Timestamp(DATA_END)
        outside = (issue_dates < start) | (issue_dates > end)
        if outside.any():
            issues.append("issue_date falls outside Jan 1, 2022 – Oct 31, 2026.")

    unknown_products = sorted(set(df["product"]) - set(PRODUCTS))
    if unknown_products:
        issues.append("Unknown product values: " + ", ".join(unknown_products))

    unknown_channels = sorted(set(df["channel"]) - set(CHANNELS))
    if unknown_channels:
        issues.append("Unknown channel values: " + ", ".join(unknown_channels))

    unknown_states = sorted(set(df["state"]) - set(STATE_TO_REGION))
    if unknown_states:
        issues.append("Unknown state codes: " + ", ".join(unknown_states))

    expected_region = df["state"].map(STATE_TO_REGION)
    if (df["region"] != expected_region).fillna(True).any():
        issues.append("region does not match the Census region for state.")

    unknown_tax = sorted(set(df["tax_status"]) - set(TAX_STATUSES))
    if unknown_tax:
        issues.append("Unknown tax_status values: " + ", ".join(unknown_tax))

    unknown_ages = sorted(set(df["annuitant_age_band"]) - set(AGE_BANDS))
    if unknown_ages:
        issues.append("Unknown annuitant_age_band values: " + ", ".join(unknown_ages))

    premium = pd.to_numeric(df["premium"], errors="coerce")
    if premium.isna().any():
        issues.append("Non-numeric premium values.")
    elif ((premium < MIN_PREMIUM) | (premium > MAX_PREMIUM)).any():
        issues.append(
            f"premium must sit between {MIN_PREMIUM:,.0f} and {MAX_PREMIUM:,.0f}."
        )

    guarantee = pd.to_numeric(df["guarantee_years"], errors="coerce")
    if guarantee.isna().any():
        issues.append("Non-numeric guarantee_years values.")
    else:
        bad_guarantee = [
            float(years) not in set(GUARANTEE_YEARS.get(product, ()))
            for product, years in zip(df["product"], guarantee, strict=True)
        ]
        if any(bad_guarantee):
            issues.append("guarantee_years is not valid for the product on that row.")

    catalog = {dist.distributor_id: dist for dist in DISTRIBUTORS}
    unknown_ids = sorted(set(df["distributor_id"]) - set(catalog))
    if unknown_ids:
        issues.append("Unknown distributor_id values: " + ", ".join(unknown_ids))
    else:
        channel_mismatch = [
            catalog[dist_id].channel != channel
            for dist_id, channel in zip(df["distributor_id"], df["channel"], strict=True)
        ]
        name_mismatch = [
            catalog[dist_id].name != name
            for dist_id, name in zip(df["distributor_id"], df["distributor_name"], strict=True)
        ]
        if any(channel_mismatch):
            issues.append("channel does not match the distributor's channel.")
        if any(name_mismatch):
            issues.append("distributor_name does not match distributor_id.")

        roster = build_agent_roster()
        bad_agents = [
            agent not in roster.get(dist_id, ())
            for dist_id, agent in zip(df["distributor_id"], df["writing_agent_id"], strict=True)
        ]
        if any(bad_agents):
            issues.append("writing_agent_id is not on that distributor's roster.")

    return ValidationResult(ok=not issues, row_count=row_count, issues=tuple(issues))
