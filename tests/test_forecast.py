"""Outlook model: flat books, seasonal books, and short histories."""

import numpy as np
import pandas as pd
import pytest

from src.forecast import (
    fit_line,
    forecast_monthly_premium,
    mape,
    multiplicative_seasonal_indices,
)


def test_fit_line_and_mape():
    slope, intercept = fit_line(np.array([2.0, 4.0, 6.0, 8.0]))
    assert slope == pytest.approx(2.0)
    assert intercept == pytest.approx(2.0)
    assert mape([100, 200], [110, 180]) == pytest.approx((0.10 + 0.10) / 2)
    assert mape([0, 0], [1, 1]) is None


def test_constant_series_forecasts_its_level():
    index = pd.date_range("2024-01-01", periods=24, freq="MS")
    series = pd.Series(100.0, index=index)
    result = forecast_monthly_premium(series, horizon=6)
    assert list(result.forecast["month"])[0] == pd.Timestamp("2026-01-01")
    assert result.forecast["forecast"].tolist() == pytest.approx([100.0] * 6)
    assert result.forecast["lower"].tolist() == pytest.approx([100.0] * 6)
    assert result.residual_std == pytest.approx(0.0, abs=1e-8)
    assert result.in_sample_mape == pytest.approx(0.0, abs=1e-8)
    assert sum(result.seasonal_indices.values()) / 12 == pytest.approx(1.0)
    assert result.months_used == 24


def test_january_is_the_strong_season():
    index = pd.date_range("2023-01-01", periods=36, freq="MS")
    series = pd.Series([200.0 if month.month == 1 else 100.0 for month in index], index=index)
    indices = multiplicative_seasonal_indices(series)
    assert indices.loc[1] > indices.loc[6]
    assert indices.mean() == pytest.approx(1.0)
    result = forecast_monthly_premium(series, horizon=12)
    by_month = result.forecast.set_index(result.forecast["month"].dt.month)["forecast"]
    assert by_month.loc[1] > by_month.loc[6]
    assert (result.forecast["forecast"] >= 0).all()
    assert (result.forecast["lower"] >= 0).all()


def test_short_history_uses_a_flat_average():
    index = pd.date_range("2026-01-01", periods=6, freq="MS")
    series = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0, 60.0], index=index)
    result = forecast_monthly_premium(series, horizon=4)
    assert len(result.forecast) == 4
    assert result.forecast["month"].iloc[0] == pd.Timestamp("2026-07-01")
    assert result.forecast["forecast"].tolist() == pytest.approx([35.0] * 4)
    assert "fewer than 12" in result.method.lower() or "average" in result.method.lower()
    assert "planning baseline" in result.narrative


def test_declining_series_does_not_forecast_negative_premium():
    index = pd.date_range("2023-01-01", periods=24, freq="MS")
    series = pd.Series(np.linspace(100, 1, 24), index=index)
    result = forecast_monthly_premium(series, horizon=6)
    assert (result.forecast["forecast"] >= 0).all()
    assert (result.forecast["lower"] >= 0).all()


def test_empty_series():
    result = forecast_monthly_premium(pd.Series(dtype=float), horizon=6)
    assert result.forecast.empty
    assert result.months_used == 0
