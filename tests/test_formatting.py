"""Compact currency and percent labels."""

import math

from src.formatting import format_count, format_day, format_pct, format_premium


def test_premium_scale():
    assert format_premium(1_234_567_890) == "$1.23B"
    assert format_premium(835_400_000) == "$835.4M"
    assert format_premium(15_500) == "$15.5K"
    assert format_premium(950) == "$950"
    assert format_premium(-2_500_000) == "-$2.5M"
    assert format_premium(None) == "—"
    assert format_premium(math.nan) == "—"


def test_percent_count_and_day():
    assert format_pct(0.084) == "+8.4%"
    assert format_pct(-0.032) == "-3.2%"
    assert format_pct(None) == "—"
    assert format_count(29481) == "29,481"
    assert format_count(None) == "—"
    assert format_day("2026-10-31") == "Oct 31, 2026"
