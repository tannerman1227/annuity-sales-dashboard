"""Display formatters shared by the dashboard and the written insights."""

from __future__ import annotations

import math

import pandas as pd


def format_premium(value: float | None) -> str:
    """Compact USD, with a sign preserved for declines."""
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return "—"
    if not math.isfinite(float(value)):
        return "—"
    number = float(value)
    sign = "-" if number < 0 else ""
    magnitude = abs(number)
    if magnitude >= 1_000_000_000:
        return f"{sign}${magnitude / 1_000_000_000:.2f}B"
    if magnitude >= 1_000_000:
        return f"{sign}${magnitude / 1_000_000:.1f}M"
    if magnitude >= 10_000:
        return f"{sign}${magnitude / 1_000:.1f}K"
    return f"{sign}${magnitude:,.0f}"


def format_pct(value: float | None, digits: int = 1) -> str:
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return "—"
    if not math.isfinite(float(value)):
        return "—"
    return f"{float(value):+.{digits}%}"


def format_count(value: int | None) -> str:
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return "—"
    if not math.isfinite(float(value)):
        return "—"
    return f"{int(value):,}"


def format_day(value) -> str:
    ts = pd.Timestamp(value)
    return f"{ts.strftime('%b')} {ts.day}, {ts.year}"
