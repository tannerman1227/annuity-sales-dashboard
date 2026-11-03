"""Six-month premium outlook.

The model is deliberately small and inspectable: multiplicative month-of-year
indices, then an ordinary least-squares line on the deseasonalized series.
It is a planning baseline for a leadership review, not a pricing model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.formatting import format_premium

FIT_WINDOW = 24
MIN_SEASONAL_MONTHS = 12
DEFAULT_HORIZON = 6


@dataclass(frozen=True)
class ForecastResult:
    forecast: pd.DataFrame
    method: str
    narrative: str
    seasonal_indices: dict[int, float]
    slope_per_month: float
    residual_std: float
    in_sample_mape: float | None
    months_used: int


def mape(actual, fitted) -> float | None:
    actual_values = np.asarray(actual, dtype=float)
    fitted_values = np.asarray(fitted, dtype=float)
    mask = np.isfinite(actual_values) & np.isfinite(fitted_values) & (np.abs(actual_values) > 1e-9)
    if not np.any(mask):
        return None
    return float(np.mean(np.abs((actual_values[mask] - fitted_values[mask]) / actual_values[mask])))


def fit_line(values: np.ndarray) -> tuple[float, float]:
    """OLS slope and intercept of y on x = 0..n-1. A single point has slope 0."""
    series = np.asarray(values, dtype=float)
    if len(series) == 0:
        return 0.0, 0.0
    if len(series) == 1:
        return 0.0, float(series[0])
    slope, intercept = np.polyfit(np.arange(len(series), dtype=float), series, 1)
    return float(slope), float(intercept)


def _as_monthly(series: pd.Series) -> pd.Series:
    if series.empty:
        return pd.Series(dtype=float)
    values = series.copy()
    values.index = pd.to_datetime(values.index)
    values = values.sort_index()
    values = values.groupby(values.index.to_period("M")).sum()
    values.index = values.index.to_timestamp()
    full = pd.date_range(values.index.min(), values.index.max(), freq="MS")
    return values.reindex(full, fill_value=0.0).astype(float)


def multiplicative_seasonal_indices(series: pd.Series) -> pd.Series:
    """Month-of-year indices (1 = January) scaled to average 1.

    With at least 24 months, each index is the mean of premium divided by a
    centered 2x12 moving average. Shorter series use each month's average
    divided by the overall average. Missing months fall back to the median
    index, then the twelve values are rescaled.
    """
    values = _as_monthly(series)
    indices = pd.Series(1.0, index=range(1, 13), dtype=float)
    if values.empty:
        return indices
    if len(values) >= FIT_WINDOW:
        trailing_average = values.rolling(12).mean()
        trend = ((trailing_average + trailing_average.shift(1)) / 2.0).shift(-6)
        ratio = values / trend.replace(0, np.nan)
        ratio = ratio.replace([np.inf, -np.inf], np.nan)
        grouped = ratio.groupby(ratio.index.month).mean()
    else:
        overall = float(values.mean())
        if overall <= 0:
            return indices
        grouped = values.groupby(values.index.month).mean() / overall
    indices = grouped.reindex(range(1, 13))
    if indices.notna().sum() == 0:
        return pd.Series(1.0, index=range(1, 13), dtype=float)
    indices = indices.fillna(float(indices.median())).clip(lower=0.05)
    indices = indices / float(indices.mean())
    indices.index = indices.index.astype(int)
    return indices


def _future_months(last_month: pd.Timestamp, horizon: int) -> pd.DatetimeIndex:
    start = (pd.Timestamp(last_month) + pd.DateOffset(months=1)).replace(day=1)
    return pd.date_range(start, periods=horizon, freq="MS")


def _narrative(method: str, horizon: int, residual_std: float, fit_mape: float | None, history_months: int, fit_months: int) -> str:
    mape_text = ""
    if fit_mape is not None and math.isfinite(fit_mape):
        mape_text = f" In-sample MAPE on the fitted months is {fit_mape:.1%}."
    if residual_std > 0:
        band = (
            f" The shaded band is the point forecast ± one in-sample residual standard deviation"
            f" ({format_premium(residual_std)}), floored at zero."
            " It is a communication aid, not a formal prediction interval."
        )
    else:
        band = ""
    return (
        f"{method} The chart projects the next {horizon} months."
        f"{band}{mape_text} "
        f"Seasonality and level are estimated from {history_months} complete months; "
        f"the trend line uses {fit_months} of them, for the selected product, channel, and state, "
        "and only through the end of the date window. "
        "This is a planning baseline for a leadership review, not a pricing, reserving, or hedging model."
    )


def _empty_result(narrative: str) -> ForecastResult:
    return ForecastResult(
        forecast=pd.DataFrame(columns=["month", "forecast", "lower", "upper"]),
        method="Insufficient history.",
        narrative=narrative,
        seasonal_indices={month: 1.0 for month in range(1, 13)},
        slope_per_month=0.0,
        residual_std=0.0,
        in_sample_mape=None,
        months_used=0,
    )


def forecast_monthly_premium(series: pd.Series, horizon: int = DEFAULT_HORIZON) -> ForecastResult:
    """Project `horizon` months of issued premium from a monthly series."""
    values = _as_monthly(series)
    if values.empty:
        return _empty_result("No complete months are available, so there is no outlook to show.")

    history_months = int(len(values))
    if history_months < MIN_SEASONAL_MONTHS:
        average = float(values.mean())
        residual_std = float(values.std(ddof=1)) if history_months > 1 else 0.0
        if not math.isfinite(residual_std):
            residual_std = 0.0
        point = max(average, 0.0)
        future = _future_months(values.index.max(), horizon)
        frame = pd.DataFrame(
            {
                "month": future,
                "forecast": point,
                "lower": max(point - residual_std, 0.0),
                "upper": point + residual_std,
            }
        )
        method = (
            "With fewer than 12 complete months, the outlook is the average of the months on hand. "
            "Seasonality is not estimated."
        )
        fit_mape = mape(values.to_numpy(), np.full(history_months, average))
        return ForecastResult(
            forecast=frame,
            method=method,
            narrative=_narrative(method, horizon, residual_std, fit_mape, history_months, history_months),
            seasonal_indices={month: 1.0 for month in range(1, 13)},
            slope_per_month=0.0,
            residual_std=residual_std,
            in_sample_mape=fit_mape,
            months_used=history_months,
        )

    indices = multiplicative_seasonal_indices(values)
    seasonal_factor = values.index.month.map(indices).astype(float)
    deseasonalized = values / seasonal_factor.to_numpy()
    fit_months = min(FIT_WINDOW, history_months)
    tail = deseasonalized.iloc[-fit_months:]
    slope, intercept = fit_line(tail.to_numpy())
    x_fit = np.arange(fit_months, dtype=float)
    fitted_level = np.clip(intercept + slope * x_fit, 0, None)
    fitted = fitted_level * tail.index.month.map(indices).to_numpy(dtype=float)
    actual = values.loc[tail.index].to_numpy(dtype=float)
    residual = actual - fitted
    residual_std = float(np.std(residual, ddof=1)) if fit_months > 1 else 0.0
    if not math.isfinite(residual_std):
        residual_std = 0.0
    fit_mape = mape(actual, fitted)

    future = _future_months(values.index.max(), horizon)
    rows = []
    for step, month in enumerate(future, start=1):
        level = max(intercept + slope * (fit_months + step - 1), 0.0)
        point = float(level * float(indices.loc[month.month]))
        rows.append(
            {
                "month": month,
                "forecast": point,
                "lower": max(point - residual_std, 0.0),
                "upper": point + residual_std,
            }
        )
    if history_months >= FIT_WINDOW:
        method = (
            "Monthly premium is split into multiplicative seasonal indices and a linear trend. "
            "Each index is the average of that calendar month relative to a centered 12-month moving average, "
            "rescaled so the twelve indices average to 1. "
            "The trend is an ordinary least-squares line on the last 24 deseasonalized months."
        )
    else:
        method = (
            "Monthly premium is split into multiplicative seasonal indices and a linear trend. "
            "With fewer than 24 months, each index is that month's average divided by the overall average, "
            "rescaled so the indices average to 1, and the trend line uses every available month."
        )
    return ForecastResult(
        forecast=pd.DataFrame(rows),
        method=method,
        narrative=_narrative(method, horizon, residual_std, fit_mape, history_months, fit_months),
        seasonal_indices={int(month): float(index) for month, index in indices.items()},
        slope_per_month=slope,
        residual_std=residual_std,
        in_sample_mape=fit_mape,
        months_used=history_months,
    )
