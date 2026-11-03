"""Shared catalog for the synthetic annuity book.

Every name in this module is fictional. Probabilities are normalized at import
so the generator, the validator, and the dashboard cannot drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass

SEED = 1227
DATA_START = "2022-01-01"
DATA_END = "2026-10-31"

PRODUCTS: tuple[str, ...] = ("Fixed", "Fixed Indexed", "Variable", "MYGA")
CHANNELS: tuple[str, ...] = ("Independent Agents", "Banks", "Broker-Dealers")
REGIONS: tuple[str, ...] = ("Northeast", "Midwest", "South", "West")
AGE_BANDS: tuple[str, ...] = ("55-59", "60-64", "65-69", "70-74", "75+")
TAX_STATUSES: tuple[str, ...] = ("Qualified", "Non-qualified")

MIN_PREMIUM = 10_000.0
MAX_PREMIUM = 1_500_000.0
QUALIFIED_RATE = 0.63

# Policy-count mix by issue year. Fixed indexed stays the core product;
# MYGA is larger in the higher-rate years; variable stays the smallest book.
PRODUCT_MIX: dict[int, dict[str, float]] = {
    2022: {"Fixed": 0.20, "Fixed Indexed": 0.40, "Variable": 0.18, "MYGA": 0.22},
    2023: {"Fixed": 0.16, "Fixed Indexed": 0.42, "Variable": 0.12, "MYGA": 0.30},
    2024: {"Fixed": 0.15, "Fixed Indexed": 0.46, "Variable": 0.11, "MYGA": 0.28},
    2025: {"Fixed": 0.15, "Fixed Indexed": 0.48, "Variable": 0.10, "MYGA": 0.27},
    2026: {"Fixed": 0.14, "Fixed Indexed": 0.50, "Variable": 0.10, "MYGA": 0.26},
}

CHANNEL_MIX: dict[str, dict[str, float]] = {
    "Fixed": {"Independent Agents": 0.45, "Banks": 0.40, "Broker-Dealers": 0.15},
    "Fixed Indexed": {"Independent Agents": 0.62, "Banks": 0.18, "Broker-Dealers": 0.20},
    "Variable": {"Independent Agents": 0.15, "Banks": 0.10, "Broker-Dealers": 0.75},
    "MYGA": {"Independent Agents": 0.28, "Banks": 0.55, "Broker-Dealers": 0.17},
}

# Median case size before the year level and the lognormal spread.
PREMIUM_MEDIAN: dict[str, float] = {
    "Fixed": 75_000.0,
    "Fixed Indexed": 115_000.0,
    "Variable": 160_000.0,
    "MYGA": 100_000.0,
}
PREMIUM_SIGMA: dict[str, float] = {
    "Fixed": 0.55,
    "Fixed Indexed": 0.50,
    "Variable": 0.60,
    "MYGA": 0.45,
}
# Scales the median. Separate from the policy-count trend so case size and
# volume can move independently, the way they do when rates change.
PREMIUM_LEVEL: dict[int, float] = {
    2022: 0.92,
    2023: 1.00,
    2024: 1.04,
    2025: 1.07,
    2026: 1.10,
}

# Expected policies per month before seasonal adjustment.
BASE_MONTHLY_POLICIES: dict[int, float] = {
    2022: 420,
    2023: 470,
    2024: 510,
    2025: 545,
    2026: 575,
}

# Annuity production is typically softer in summer and heavier in the fourth
# quarter, when year-end money is in motion.
SEASONALITY: dict[int, float] = {
    1: 1.08,
    2: 0.94,
    3: 1.06,
    4: 0.98,
    5: 0.97,
    6: 0.90,
    7: 0.88,
    8: 0.92,
    9: 1.03,
    10: 1.10,
    11: 1.12,
    12: 1.28,
}

GUARANTEE_YEARS: dict[str, tuple[int, ...]] = {
    "Fixed": (3, 5, 7),
    "Fixed Indexed": (5, 7, 10),
    "Variable": (0,),
    "MYGA": (3, 5, 7),
}
GUARANTEE_WEIGHTS: dict[str, tuple[float, ...]] = {
    "Fixed": (0.25, 0.50, 0.25),
    "Fixed Indexed": (0.20, 0.45, 0.35),
    "Variable": (1.0,),
    "MYGA": (0.35, 0.45, 0.20),
}

AGE_WEIGHTS: tuple[float, ...] = (0.12, 0.24, 0.30, 0.22, 0.12)

# Census regions, including DC in the South.
STATE_TO_REGION: dict[str, str] = {
    "CT": "Northeast",
    "ME": "Northeast",
    "MA": "Northeast",
    "NH": "Northeast",
    "RI": "Northeast",
    "VT": "Northeast",
    "NJ": "Northeast",
    "NY": "Northeast",
    "PA": "Northeast",
    "IL": "Midwest",
    "IN": "Midwest",
    "IA": "Midwest",
    "KS": "Midwest",
    "MI": "Midwest",
    "MN": "Midwest",
    "MO": "Midwest",
    "NE": "Midwest",
    "ND": "Midwest",
    "OH": "Midwest",
    "SD": "Midwest",
    "WI": "Midwest",
    "DE": "South",
    "FL": "South",
    "GA": "South",
    "MD": "South",
    "NC": "South",
    "SC": "South",
    "VA": "South",
    "DC": "South",
    "WV": "South",
    "AL": "South",
    "KY": "South",
    "MS": "South",
    "TN": "South",
    "AR": "South",
    "LA": "South",
    "OK": "South",
    "TX": "South",
    "AZ": "West",
    "CO": "West",
    "ID": "West",
    "MT": "West",
    "NV": "West",
    "NM": "West",
    "UT": "West",
    "WY": "West",
    "AK": "West",
    "CA": "West",
    "HI": "West",
    "OR": "West",
    "WA": "West",
}

# Roughly population-weighted, with extra weight on large annuity states.
STATE_WEIGHTS: dict[str, float] = {
    "AL": 1.5,
    "AK": 0.2,
    "AZ": 2.4,
    "AR": 0.9,
    "CA": 8.5,
    "CO": 1.8,
    "CT": 1.1,
    "DE": 0.3,
    "DC": 0.2,
    "FL": 7.8,
    "GA": 3.0,
    "HI": 0.4,
    "ID": 0.6,
    "IL": 3.6,
    "IN": 2.0,
    "IA": 1.4,
    "KS": 0.9,
    "KY": 1.3,
    "LA": 1.3,
    "ME": 0.4,
    "MD": 1.7,
    "MA": 2.0,
    "MI": 3.0,
    "MN": 1.8,
    "MS": 0.8,
    "MO": 1.8,
    "MT": 0.3,
    "NE": 0.6,
    "NV": 0.9,
    "NH": 0.4,
    "NJ": 2.6,
    "NM": 0.6,
    "NY": 5.5,
    "NC": 3.2,
    "ND": 0.2,
    "OH": 3.4,
    "OK": 1.1,
    "OR": 1.2,
    "PA": 3.8,
    "RI": 0.3,
    "SC": 1.6,
    "SD": 0.3,
    "TN": 2.0,
    "TX": 7.2,
    "UT": 0.9,
    "VT": 0.2,
    "VA": 2.4,
    "WA": 2.1,
    "WV": 0.5,
    "WI": 1.8,
    "WY": 0.2,
}


@dataclass(frozen=True)
class Distributor:
    distributor_id: str
    name: str
    channel: str
    weight: float


# Fictional firms. Weights set a realistic concentration curve inside each channel.
DISTRIBUTORS: tuple[Distributor, ...] = (
    Distributor("DST-1101", "Summit Peak IMO", "Independent Agents", 6.0),
    Distributor("DST-1102", "Harborlight Financial", "Independent Agents", 4.6),
    Distributor("DST-1103", "Prairie Ridge Marketing", "Independent Agents", 3.8),
    Distributor("DST-1104", "Lone Star Annuity Group", "Independent Agents", 3.4),
    Distributor("DST-1105", "Cascade Independent", "Independent Agents", 2.7),
    Distributor("DST-1106", "Heartland Producer Network", "Independent Agents", 2.4),
    Distributor("DST-1107", "Blue Mesa IMO", "Independent Agents", 2.1),
    Distributor("DST-1108", "Ironwood Marketing", "Independent Agents", 1.8),
    Distributor("DST-1109", "Redbird Producer Group", "Independent Agents", 1.5),
    Distributor("DST-1110", "Northfork Annuity Marketing", "Independent Agents", 1.3),
    Distributor("DST-1111", "Clearwater Independent", "Independent Agents", 1.1),
    Distributor("DST-1112", "Sable Point IMO", "Independent Agents", 0.9),
    Distributor("DST-1113", "High Plains Marketing", "Independent Agents", 0.8),
    Distributor("DST-1114", "Westridge Producer Group", "Independent Agents", 0.7),
    Distributor("DST-2101", "First Meridian Bank", "Banks", 4.2),
    Distributor("DST-2102", "Lakeshore Community Bank", "Banks", 3.3),
    Distributor("DST-2103", "Redwood National Bank", "Banks", 2.9),
    Distributor("DST-2104", "Copperline Financial", "Banks", 2.3),
    Distributor("DST-2105", "Piedmont Trust Bank", "Banks", 2.0),
    Distributor("DST-2106", "Grant Street Bank", "Banks", 1.6),
    Distributor("DST-2107", "Bayou Federal Bank", "Banks", 1.3),
    Distributor("DST-2108", "Cedar Valley Bank", "Banks", 1.1),
    Distributor("DST-2109", "Hightower Savings Bank", "Banks", 0.9),
    Distributor("DST-2110", "Solace Bank & Trust", "Banks", 0.7),
    Distributor("DST-3101", "Northstar Brokerage", "Broker-Dealers", 4.4),
    Distributor("DST-3102", "Vantage Securities", "Broker-Dealers", 3.5),
    Distributor("DST-3103", "Atlas Wealth Partners", "Broker-Dealers", 2.9),
    Distributor("DST-3104", "Keystone Capital BD", "Broker-Dealers", 2.4),
    Distributor("DST-3105", "Meridian Advisory Network", "Broker-Dealers", 2.0),
    Distributor("DST-3106", "Halcyon Securities", "Broker-Dealers", 1.7),
    Distributor("DST-3107", "Oak & Elm Wealth", "Broker-Dealers", 1.4),
    Distributor("DST-3108", "Lantern Brokerage", "Broker-Dealers", 1.2),
    Distributor("DST-3109", "Fieldguide Securities", "Broker-Dealers", 1.0),
    Distributor("DST-3110", "Brightline Advisory", "Broker-Dealers", 0.9),
    Distributor("DST-3111", "Stonebridge Wealth BD", "Broker-Dealers", 0.8),
    Distributor("DST-3112", "Kindling Capital", "Broker-Dealers", 0.7),
)

REQUIRED_COLUMNS: tuple[str, ...] = (
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
    "tax_status",
    "annuitant_age_band",
    "guarantee_years",
)

MONTH_ABBR: tuple[str, ...] = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def build_agent_roster() -> dict[str, tuple[str, ...]]:
    """Deterministic writing-agent IDs for each fictional distributor."""
    roster: dict[str, tuple[str, ...]] = {}
    next_id = 100_000
    for dist in DISTRIBUTORS:
        count = 24 + int(round(dist.weight * 14))
        roster[dist.distributor_id] = tuple(
            f"AGT-{next_id + offset}" for offset in range(count)
        )
        next_id += count
    return roster


def _assert_probability_map(name: str, mapping: dict, expected_keys: tuple[str, ...] | None = None) -> None:
    for key, weights in mapping.items():
        values = list(weights.values()) if isinstance(weights, dict) else list(weights)
        if expected_keys is not None and isinstance(weights, dict):
            if tuple(weights) != expected_keys and set(weights) != set(expected_keys):
                raise ValueError(f"{name}[{key}] keys do not match the catalog")
        total = float(sum(values))
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"{name}[{key}] sums to {total}, expected 1")


def _validate_catalog() -> None:
    if set(STATE_TO_REGION) != set(STATE_WEIGHTS):
        raise ValueError("State region map and state weights cover different states")
    if len(STATE_TO_REGION) != 51:
        raise ValueError("Expected 50 states plus DC")
    if len({d.distributor_id for d in DISTRIBUTORS}) != len(DISTRIBUTORS):
        raise ValueError("Distributor ids must be unique")
    if len({d.name for d in DISTRIBUTORS}) != len(DISTRIBUTORS):
        raise ValueError("Distributor names must be unique")
    for dist in DISTRIBUTORS:
        if dist.channel not in CHANNELS:
            raise ValueError(f"{dist.name} has an unknown channel")
    _assert_probability_map("PRODUCT_MIX", PRODUCT_MIX, PRODUCTS)
    _assert_probability_map("CHANNEL_MIX", CHANNEL_MIX, CHANNELS)
    _assert_probability_map("GUARANTEE_WEIGHTS", GUARANTEE_WEIGHTS)
    if abs(sum(AGE_WEIGHTS) - 1.0) > 1e-9:
        raise ValueError("AGE_WEIGHTS must sum to 1")
    for product, years in GUARANTEE_YEARS.items():
        if len(years) != len(GUARANTEE_WEIGHTS[product]):
            raise ValueError(f"Guarantee options and weights differ for {product}")
    for year in range(2022, 2027):
        if year not in PRODUCT_MIX or year not in PREMIUM_LEVEL or year not in BASE_MONTHLY_POLICIES:
            raise ValueError(f"Missing year-level parameters for {year}")
    if set(SEASONALITY) != set(range(1, 13)):
        raise ValueError("Seasonality must cover months 1-12")


_validate_catalog()
