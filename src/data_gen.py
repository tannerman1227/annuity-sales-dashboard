"""Seeded generator for a fictional annuity sales book.

Run from the repo root:

    python -m src.data_gen

The default seed is 1227. With the NumPy version pinned in requirements.txt,
that seed reproduces data/annuity_sales.csv.
"""

from __future__ import annotations

import calendar
from pathlib import Path

import numpy as np
import pandas as pd

from src.constants import (
    AGE_BANDS,
    AGE_WEIGHTS,
    BASE_MONTHLY_POLICIES,
    CHANNELS,
    CHANNEL_MIX,
    DATA_END,
    DISTRIBUTORS,
    GUARANTEE_WEIGHTS,
    GUARANTEE_YEARS,
    MAX_PREMIUM,
    MIN_PREMIUM,
    PREMIUM_LEVEL,
    PREMIUM_MEDIAN,
    PREMIUM_SIGMA,
    PRODUCTS,
    PRODUCT_MIX,
    QUALIFIED_RATE,
    REQUIRED_COLUMNS,
    SEASONALITY,
    SEED,
    STATE_TO_REGION,
    STATE_WEIGHTS,
    build_agent_roster,
)
from src.validation import validate_sales


def _weighted_choice(rng: np.random.Generator, labels: list[str] | tuple, weights, size: int):
    values = np.asarray(list(labels))
    probabilities = np.asarray(list(weights), dtype=float)
    probabilities = probabilities / probabilities.sum()
    return rng.choice(values, size=size, p=probabilities)


def iter_months(end: str = DATA_END):
    last = pd.Timestamp(end)
    cursor = pd.Timestamp("2022-01-01")
    while cursor <= last:
        yield cursor.year, cursor.month
        cursor = cursor + pd.DateOffset(months=1)


def generate_sales(seed: int = SEED, end: str = DATA_END) -> pd.DataFrame:
    """Build one issued-policy row per contract. `seed` makes the book repeatable."""
    rng = np.random.default_rng(seed)
    roster = build_agent_roster()
    names = {dist.distributor_id: dist.name for dist in DISTRIBUTORS}
    state_labels = list(STATE_WEIGHTS)
    state_weights = [STATE_WEIGHTS[state] for state in state_labels]
    chunks: list[pd.DataFrame] = []
    policy_seq = 1_000_001

    for year, month in iter_months(end):
        expected = BASE_MONTHLY_POLICIES[year] * SEASONALITY[month]
        count = int(rng.poisson(expected))
        if count == 0:
            continue

        products = _weighted_choice(rng, PRODUCTS, [PRODUCT_MIX[year][p] for p in PRODUCTS], count)
        channels = np.empty(count, dtype=object)
        guarantees = np.empty(count, dtype=int)
        premiums = np.empty(count, dtype=float)
        for product in PRODUCTS:
            selected = np.flatnonzero(products == product)
            if len(selected) == 0:
                continue
            mix = CHANNEL_MIX[product]
            channels[selected] = _weighted_choice(
                rng, CHANNELS, [mix[channel] for channel in CHANNELS], len(selected)
            )
            guarantees[selected] = _weighted_choice(
                rng,
                GUARANTEE_YEARS[product],
                GUARANTEE_WEIGHTS[product],
                len(selected),
            ).astype(int)
            median = PREMIUM_MEDIAN[product] * PREMIUM_LEVEL[year]
            draw = rng.lognormal(mean=np.log(median), sigma=PREMIUM_SIGMA[product], size=len(selected))
            premiums[selected] = np.round(np.clip(draw, MIN_PREMIUM, MAX_PREMIUM), 2)

        distributors = np.empty(count, dtype=object)
        for channel in CHANNELS:
            selected = np.flatnonzero(channels == channel)
            if len(selected) == 0:
                continue
            members = [dist for dist in DISTRIBUTORS if dist.channel == channel]
            distributors[selected] = _weighted_choice(
                rng,
                [dist.distributor_id for dist in members],
                [dist.weight for dist in members],
                len(selected),
            )

        agents = np.empty(count, dtype=object)
        for dist_id, pool in roster.items():
            selected = np.flatnonzero(distributors == dist_id)
            if len(selected) == 0:
                continue
            agents[selected] = rng.choice(np.asarray(pool), size=len(selected))

        states = _weighted_choice(rng, state_labels, state_weights, count)
        days_in_month = calendar.monthrange(year, month)[1]
        days = rng.integers(1, days_in_month + 1, size=count)
        issue_dates = [f"{year}-{month:02d}-{int(day):02d}" for day in days]
        tax_status = np.where(rng.random(count) < QUALIFIED_RATE, "Qualified", "Non-qualified")
        ages = _weighted_choice(rng, AGE_BANDS, AGE_WEIGHTS, count)
        policy_ids = [f"POL-{policy_seq + offset}" for offset in range(count)]
        policy_seq += count

        chunks.append(
            pd.DataFrame(
                {
                    "policy_id": policy_ids,
                    "issue_date": issue_dates,
                    "product": products,
                    "channel": channels,
                    "state": states,
                    "region": [STATE_TO_REGION[state] for state in states],
                    "distributor_id": distributors,
                    "distributor_name": [names[dist_id] for dist_id in distributors],
                    "writing_agent_id": agents,
                    "premium": premiums,
                    "tax_status": tax_status,
                    "annuitant_age_band": ages,
                    "guarantee_years": guarantees,
                }
            )
        )

    frame = pd.concat(chunks, ignore_index=True)
    frame["issue_date"] = pd.to_datetime(frame["issue_date"])
    frame["premium"] = frame["premium"].astype(float).round(2)
    frame["guarantee_years"] = frame["guarantee_years"].astype(int)
    frame = frame.sort_values(["issue_date", "policy_id"], kind="mergesort").reset_index(drop=True)
    return frame[list(REQUIRED_COLUMNS)]


def write_sales(path: Path | None = None, seed: int = SEED) -> Path:
    destination = path or Path(__file__).resolve().parents[1] / "data" / "annuity_sales.csv"
    frame = generate_sales(seed=seed)
    result = validate_sales(frame)
    if not result.ok:
        detail = "\n".join(result.issues)
        raise RuntimeError(f"Generated data failed validation:\n{detail}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False, float_format="%.2f")
    return destination


def main() -> None:
    destination = write_sales()
    frame = pd.read_csv(destination, parse_dates=["issue_date"])
    print(f"Wrote {len(frame):,} synthetic policies to {destination}")
    print(f"Issued premium ${frame['premium'].sum():,.0f}")
    print(f"Issue dates {frame['issue_date'].min().date()} to {frame['issue_date'].max().date()}")
    print("Synthetic demonstration data. Not an insurer's results.")


if __name__ == "__main__":
    main()
