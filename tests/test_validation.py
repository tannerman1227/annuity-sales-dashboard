"""Validation rules, including a pass on one fully linked synthetic row."""

import pandas as pd

from src.constants import DISTRIBUTORS, build_agent_roster
from src.validation import validate_sales


def valid_frame(**overrides) -> pd.DataFrame:
    distributor = next(dist for dist in DISTRIBUTORS if dist.channel == "Banks")
    agent = build_agent_roster()[distributor.distributor_id][0]
    row = {
        "policy_id": "POL-1000001",
        "issue_date": pd.Timestamp("2024-06-15"),
        "product": "MYGA",
        "channel": "Banks",
        "state": "TX",
        "region": "South",
        "distributor_id": distributor.distributor_id,
        "distributor_name": distributor.name,
        "writing_agent_id": agent,
        "premium": 100_000.0,
        "tax_status": "Qualified",
        "annuitant_age_band": "65-69",
        "guarantee_years": 5,
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_valid_row_passes():
    result = validate_sales(valid_frame())
    assert result.ok
    assert result.issues == ()
    assert result.row_count == 1


def test_missing_column_stops_early():
    frame = valid_frame().drop(columns=["premium"])
    result = validate_sales(frame)
    assert not result.ok
    assert any("premium" in issue for issue in result.issues)


def test_duplicate_policy_negative_premium_and_bad_region():
    frame = pd.concat([valid_frame(), valid_frame()], ignore_index=True)
    result = validate_sales(frame)
    assert any("duplicate" in issue for issue in result.issues)

    cheap = validate_sales(valid_frame(premium=-50))
    assert any("premium" in issue for issue in cheap.issues)

    region = validate_sales(valid_frame(region="Northeast"))
    assert any("region" in issue for issue in region.issues)


def test_product_guarantee_and_agent_referential_checks():
    variable = validate_sales(valid_frame(product="Variable", guarantee_years=5))
    assert any("guarantee_years" in issue for issue in variable.issues)

    stranger = validate_sales(valid_frame(writing_agent_id="AGT-999999"))
    assert any("writing_agent_id" in issue for issue in stranger.issues)

    unknown = validate_sales(valid_frame(distributor_id="DST-9999", distributor_name="Nobody"))
    assert any("distributor_id" in issue for issue in unknown.issues)


def test_date_outside_the_book():
    result = validate_sales(valid_frame(issue_date=pd.Timestamp("2021-12-31")))
    assert any("issue_date" in issue for issue in result.issues)
