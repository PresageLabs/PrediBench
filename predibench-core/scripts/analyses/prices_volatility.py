#!/usr/bin/env python3
"""
Analysis of market probabilities Brier score evolution over time.

This script analyzes how the Brier scores of market predicted probabilities evolve
as a function of time to event end, showing market accuracy improvement over time.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pywt
from long_time_series_request import _HistoricalTimeSeriesRequest
from predibench.backend.data_loader import (
    load_saved_events,
)
from predibench.backend.data_model import EventBackend
from predibench.backend.events import get_non_duplicated_events
from predibench.common_models import DataPoint
from predibench.logger_config import get_logger
from predibench.utils import apply_template
from tqdm import tqdm

logger = get_logger(__name__)

# Threshold to accept a market as clearly resolved at its stopping time
# We treat prices <= 0.05 as NO resolved, and >= 0.95 as YES resolved
EPSILON_TERMINAL = 0.05

HORIZONS = ["1h", "6h", "12h", "1d", "2d", "4d", "7d", "14d", "30d"]


def _horizon_to_hours(horizon: str) -> int:
    """Convert horizon string to hours."""
    if horizon.endswith("h"):
        return int(horizon[:-1])
    elif horizon.endswith("d"):
        return int(horizon[:-1]) * 24
    else:
        raise ValueError(f"Unknown horizon format: {horizon}")


def _get_max_horizon_hours() -> int:
    """Get the maximum horizon in hours from HORIZONS."""
    return max(_horizon_to_hours(h) for h in HORIZONS)


# Outcome stats for logging/diagnostics
OUTCOME_STATS: dict[str, int] = {
    "eligible_markets": 0,  # markets with end passed and price data
    "resolved_markets": 0,  # markets that hit <=0.1 or >=0.9
    "dropped_unresolved_markets": 0,  # eligible but never hit thresholds
}

# Export all figures to dedicated subfolder under frontend public
repo_root = Path(__file__).resolve().parents[3]
base_dir = repo_root / "predibench-frontend-react/public/prices_volatility"
base_dir.mkdir(parents=True, exist_ok=True)

# Also export HTML files to analyses folder for inspection
analyses_dir = repo_root / "analyses" / "prices_volatility"
analyses_dir.mkdir(parents=True, exist_ok=True)


def export_figure(fig, slug):
    # Save JSON for frontend
    json_file_path = base_dir / f"{slug}.json"
    fig.write_json(str(json_file_path))
    logger.info(f"Saved Brier plot JSON to {json_file_path}")

    # Save HTML for inspection
    html_file_path = analyses_dir / f"{slug}.html"
    fig.write_html(str(html_file_path))
    logger.info(f"Saved Brier plot HTML to {html_file_path}")


def calculate_brier_score(predicted_prob: float, actual_outcome: int) -> float:
    """
    Compute the Brier score for a single binary prediction.

    Args:
        predicted_prob: Probability assigned to the positive class (between 0 and 1)
        actual_outcome: Actual outcome (0 or 1)
    """
    predicted_prob = float(np.clip(predicted_prob, 0.0, 1.0))
    assert actual_outcome in (0, 1)
    # Return sqrt of Brier (i.e., absolute error) to reduce squaring effects
    return abs(predicted_prob - actual_outcome)


def _to_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware in UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_datetime_mixed(value: str | datetime) -> datetime:
    """Parse a single datetime in mixed ISO formats into tz-aware UTC datetime."""
    return pd.to_datetime(value, utc=True, format="mixed").to_pydatetime()


def _parse_datetime_index_mixed(values: list[str] | list[datetime]) -> pd.DatetimeIndex:
    """Parse a list of datetimes in mixed formats to a tz-aware UTC DatetimeIndex."""
    return pd.to_datetime(values, utc=True, format="mixed")


def _compute_effective_end_datetime(
    market, event_end: datetime | None
) -> datetime | None:
    """
    Determine effective end as the timestamp when prices stop moving (last change).
    If there was never a change, fall back to the last timestamp in the series.
    Returns tz-aware UTC datetime.
    """
    if getattr(market, "prices", None):
        ts = pd.Series(
            [dp.value for dp in market.prices],
            index=_parse_datetime_index_mixed([dp.date for dp in market.prices]),
        ).sort_index()
        if len(ts) == 0:
            return _to_utc(event_end)
        # Find the last index where the price changed compared to previous sample
        change_mask = ts.ne(ts.shift(1))
        if change_mask.any():
            last_change_idx = ts.index[change_mask][-1]
            return last_change_idx.to_pydatetime()
        # Never changed: use the last timestamp
        return ts.index.max().to_pydatetime()
    return _to_utc(event_end)


def _estimate_mutual_information_binned(
    x: np.ndarray, y: np.ndarray, bins: int = 10
) -> float:
    """
    Estimate mutual information using binning approach.
    """
    if len(x) != len(y) or len(x) < 10:
        return 0.0

    try:
        # Create bins based on quantiles
        x_bins = pd.qcut(x, q=bins, duplicates="drop", retbins=True)[1]
        y_bins = pd.qcut(y, q=bins, duplicates="drop", retbins=True)[1]

        # Digitize the data
        x_binned = np.digitize(x, x_bins) - 1
        y_binned = np.digitize(y, y_bins) - 1

        # Ensure valid range
        x_binned = np.clip(x_binned, 0, len(x_bins) - 2)
        y_binned = np.clip(y_binned, 0, len(y_bins) - 2)

        # Calculate joint and marginal distributions
        joint_hist = np.histogram2d(
            x_binned, y_binned, bins=[len(x_bins) - 1, len(y_bins) - 1]
        )[0]
        x_hist = np.histogram(x_binned, bins=len(x_bins) - 1)[0]
        y_hist = np.histogram(y_binned, bins=len(y_bins) - 1)[0]

        # Normalize to probabilities
        joint_prob = joint_hist / np.sum(joint_hist)
        x_prob = x_hist / np.sum(x_hist)
        y_prob = y_hist / np.sum(y_hist)

        # Calculate mutual information
        mi = 0.0
        for i in range(len(x_prob)):
            for j in range(len(y_prob)):
                if joint_prob[i, j] > 0 and x_prob[i] > 0 and y_prob[j] > 0:
                    mi += joint_prob[i, j] * np.log2(
                        joint_prob[i, j] / (x_prob[i] * y_prob[j])
                    )

        return max(0.0, mi)

    except Exception:
        return 0.0


def calculate_mutual_information_decay(price_series: pd.Series) -> dict:
    """
    Calculate mutual information decay vs lag for price returns.

    Args:
        price_series: Time series of prices

    Returns:
        Dictionary with lags, MI values, and information half-life
    """
    # Calculate MI for available horizons, not just the maximum
    if len(price_series) < 50:  # Need minimum data for any meaningful analysis
        return {"lags": [], "mi_values": [], "half_life": None}

    # Compute returns (price differences)
    returns = price_series.diff().dropna()

    # Winsorize extreme returns (0.5-99.5th percentile)
    lower_bound = returns.quantile(0.005)
    upper_bound = returns.quantile(0.995)
    returns = returns.clip(lower=lower_bound, upper=upper_bound)

    if len(returns) < 10:
        return {"lags": [], "mi_values": [], "half_life": None}

    lags = []
    mi_values = []

    # Calculate MI for lags up to 14 days (markets are pre-filtered to have this much data)
    max_available_lag = _horizon_to_hours("14d")  # 336 hours

    for lag in range(1, max_available_lag + 1):
        # Create lagged series
        r_t = returns.iloc[lag:].values
        r_t_lag = returns.iloc[:-lag].values

        # Calculate mutual information using binning
        mi = _estimate_mutual_information_binned(r_t, r_t_lag)

        lags.append(lag)
        mi_values.append(mi)

    # Calculate information half-life
    half_life = None
    if len(mi_values) > 1 and mi_values[0] > 0:
        half_mi = mi_values[0] * 0.5
        for i, mi in enumerate(mi_values):
            if mi <= half_mi:
                half_life = lags[i]
                break

    return {"lags": lags, "mi_values": mi_values, "half_life": half_life}


def calculate_autocorrelation_half_life(price_series: pd.Series) -> dict:
    """
    Calculate autocorrelation function and AR(1) half-life for price returns.

    Args:
        price_series: Time series of prices

    Returns:
        Dictionary with ACF values, AR(1) half-life, and ACF zero-crossing
    """
    # Calculate ACF for available horizons, not just the maximum
    if len(price_series) < 50:  # Need minimum data for any meaningful analysis
        return {
            "lags": [],
            "acf_values": [],
            "ar1_half_life": None,
            "acf_zero_crossing": None,
        }

    # Compute returns
    returns = price_series.diff().dropna()

    # Winsorize extreme returns
    lower_bound = returns.quantile(0.005)
    upper_bound = returns.quantile(0.995)
    returns = returns.clip(lower=lower_bound, upper=upper_bound)

    if len(returns) < 10:
        return {
            "lags": [],
            "acf_values": [],
            "ar1_half_life": None,
            "acf_zero_crossing": None,
        }

    # Calculate autocorrelation function
    horizon_hours = [_horizon_to_hours(h) for h in HORIZONS]
    # Be less restrictive - allow up to 30 days if we have at least 30 days + some buffer
    max_available_lag = min(
        max(horizon_hours), len(returns) - 50
    )  # Keep 50 points minimum for correlation

    lags = list(range(1, max_available_lag + 1))
    acf_values = []

    for lag in lags:
        if len(returns) <= lag:
            break
        correlation = returns.autocorr(lag=lag)
        if pd.isna(correlation):
            break
        acf_values.append(correlation)

    # Find ACF zero crossing
    acf_zero_crossing = None
    for i, acf in enumerate(acf_values):
        if abs(acf) < 0.05:  # Effectively zero
            acf_zero_crossing = lags[i]
            break

    # Calculate AR(1) half-life
    ar1_half_life = None
    if len(returns) > 1:
        # Fit AR(1) model: r_t = phi * r_{t-1} + epsilon_t
        r_t = returns.iloc[1:].values
        r_t_1 = returns.iloc[:-1].values

        if len(r_t) > 0 and np.var(r_t_1) > 0:
            phi = np.corrcoef(r_t, r_t_1)[0, 1] * np.std(r_t) / np.std(r_t_1)

            # Half-life formula: HL = -ln(2) / ln(phi)
            if 0 < phi < 1:
                ar1_half_life = -np.log(2) / np.log(phi)
            elif phi <= 0:
                ar1_half_life = 1  # Immediate mean reversion

    return {
        "lags": lags[: len(acf_values)],
        "acf_values": acf_values,
        "ar1_half_life": ar1_half_life,
        "acf_zero_crossing": acf_zero_crossing,
    }


def calculate_wavelet_variance(price_series: pd.Series, wavelet: str = "db4") -> dict:
    """
    Calculate wavelet variance using MODWT (Maximal Overlap Discrete Wavelet Transform).

    Args:
        price_series: Time series of prices
        wavelet: Wavelet type for decomposition

    Returns:
        Dictionary with horizons, wavelet variances, and elbow scale
    """
    # Basic check for minimum data
    if len(price_series) < 16:
        return {"horizons": [], "variances": [], "elbow_scale": None}

    # Compute returns
    returns = price_series.diff().dropna()

    # Winsorize extreme returns
    lower_bound = returns.quantile(0.005)
    upper_bound = returns.quantile(0.995)
    returns = returns.clip(lower=lower_bound, upper=upper_bound)

    if len(returns) < 16:  # Minimum length for meaningful decomposition
        return {"horizons": [], "variances": [], "elbow_scale": None}

    horizons = []
    variances = []

    # Use natural wavelet decomposition with powers of 2 time scales
    returns_array = returns.values

    # Perform wavelet decomposition
    max_possible_levels = min(8, pywt.dwt_max_level(len(returns_array), wavelet))

    if max_possible_levels == 0:
        raise ValueError(
            f"Insufficient data for wavelet decomposition: {len(returns_array)} points"
        )

    coeffs = pywt.wavedec(returns_array, wavelet, level=max_possible_levels)

    # Use natural wavelet time scales (2^j hours)
    # For hourly sampling: Scale at level j ≈ 2^j hours
    for j in range(1, len(coeffs)):  # Skip approximation coeffs (index 0)
        detail_coeffs = coeffs[j]

        if len(detail_coeffs) == 0:
            continue

        time_scale_hours = 2**j  # Level j captures fluctuations at ~2^j hours

        # Check if we have enough time span for this time scale analysis
        time_span_hours = (
            price_series.index.max() - price_series.index.min()
        ).total_seconds() // 3600
        if time_span_hours < time_scale_hours:
            continue

        wvar = np.var(detail_coeffs)

        horizons.append(f"{time_scale_hours}h")
        variances.append(wvar)

    # Find elbow in variance curve (point of diminishing returns)
    elbow_scale = None
    if len(variances) > 2:
        # Calculate second differences to find elbow
        var_diffs = np.diff(np.diff(variances))
        if len(var_diffs) > 0:
            # Find the horizon where curvature changes most
            elbow_idx = (
                np.argmax(np.abs(var_diffs)) + 2
            )  # +2 due to double differencing
            if elbow_idx < len(horizons):
                elbow_scale = elbow_idx + 1  # Return 1-based index

    return {
        "horizons": horizons,
        "variances": variances,
        "elbow_scale": elbow_scale,
    }


def get_event_outcomes(events: list[EventBackend]) -> dict[str, int]:
    """
    Extract actual outcomes for events that have resolved.

    Returns:
        Dictionary mapping event_id to outcome (0 or 1)
    """
    event_outcomes = {}

    # reset outcome stats
    OUTCOME_STATS["eligible_markets"] = 0
    OUTCOME_STATS["resolved_markets"] = 0
    OUTCOME_STATS["dropped_unresolved_markets"] = 0

    for event in events:
        # Check if event has resolved
        end_dt = _to_utc(event.end_datetime)
        if end_dt and datetime.now(timezone.utc) > end_dt:
            # Determine outcome from final price at effective end (or event end)
            for market in event.markets:
                if market.prices is None or len(market.prices) == 0:
                    continue
                OUTCOME_STATS["eligible_markets"] += 1
                eff_end = _compute_effective_end_datetime(market, event.end_datetime)
                eff_end = _to_utc(eff_end)
                ts = pd.Series(
                    [dp.value for dp in market.prices],
                    index=_parse_datetime_index_mixed(
                        [dp.date for dp in market.prices]
                    ),
                ).sort_index()
                # Take the last price at or before effective end
                ts = ts.loc[ts.index <= eff_end]
                if ts.empty:
                    OUTCOME_STATS["dropped_unresolved_markets"] += 1
                    continue
                final_price = float(ts.iloc[-1])
                # Only accept clearly resolved markets
                if final_price >= (1 - EPSILON_TERMINAL):
                    OUTCOME_STATS["resolved_markets"] += 1
                    event_outcomes[event.id] = 1
                    break  # Only process first qualifying market per event
                elif final_price <= EPSILON_TERMINAL:
                    OUTCOME_STATS["resolved_markets"] += 1
                    event_outcomes[event.id] = 0
                    break
                else:
                    OUTCOME_STATS["dropped_unresolved_markets"] += 1
                    # Try next market for this event if available
                    continue

    return event_outcomes


def calculate_time_to_event_brier_scores(events: list[EventBackend]) -> pd.DataFrame:
    """
    Calculate Brier scores at different time points before event end.

    Returns:
        DataFrame with columns: event_id, hours_to_end, market_price, brier_score, actual_outcome
    """
    event_outcomes = get_event_outcomes(events)
    logger.info(f"Found {len(event_outcomes)} resolved events")
    if OUTCOME_STATS["eligible_markets"] > 0:
        dropped_ratio = (
            OUTCOME_STATS["dropped_unresolved_markets"]
            / OUTCOME_STATS["eligible_markets"]
        )
        logger.info(
            f"Outcome resolution filter: eligible_markets={OUTCOME_STATS['eligible_markets']}, "
            f"resolved_markets={OUTCOME_STATS['resolved_markets']}, "
            f"dropped_unresolved_markets={OUTCOME_STATS['dropped_unresolved_markets']} "
            f"(drop ratio={dropped_ratio:.2%})"
        )

    results = []

    for event in events:
        if event.id not in event_outcomes:
            continue

        actual_outcome = event_outcomes[event.id]

        for market in event.markets:
            if market.prices is None or len(market.prices) == 0:
                continue

            # Compute effective end once per market (first ~0/100% hit or event end)
            effective_end_dt_utc = _compute_effective_end_datetime(
                market, event.end_datetime
            )
            if effective_end_dt_utc is None:
                continue

            # Process each price point
            for price_point in market.prices:
                # Parse the date from the price point
                price_date = _parse_datetime_mixed(price_point.date)

                # Calculate hours to effective end
                hours_to_end = (
                    effective_end_dt_utc - price_date
                ).total_seconds() / 3600

                # Only consider prices before event end
                if hours_to_end > 0:
                    market_price = price_point.value
                    results.append(
                        {
                            "event_id": event.id,
                            "market_id": market.id,
                            "event_title": event.title[:50] + "..."
                            if len(event.title) > 50
                            else event.title,
                            "hours_to_end": hours_to_end,
                            "market_price": market_price,
                            "brier_score": calculate_brier_score(
                                market_price, actual_outcome
                            ),
                            "actual_outcome": actual_outcome,
                            "price_date": price_date,
                        }
                    )

            break  # Only process first market per event for now

    return pd.DataFrame(results)


def analyze_market_volatility_measures(events: list[EventBackend]) -> pd.DataFrame:
    """
    Apply all three volatility measures to markets with sufficient price data.

    Each analysis function will now handle per-horizon filtering internally.

    Returns:
        DataFrame with volatility analysis results for each market
    """
    results = []
    data_length_stats = []
    data_span_hours = []  # Track time spans in hours

    for event in events:
        for market in event.markets:
            if market.prices is None:
                continue

            data_length = len(market.prices)
            data_length_stats.append(data_length)

            # Apply basic minimum filter - need at least some data
            if data_length < 50:
                continue

            # Convert prices to pandas Series
            try:
                timestamps = [_parse_datetime_mixed(dp.date) for dp in market.prices]
                prices = [dp.value for dp in market.prices]
                price_series = pd.Series(
                    prices, index=pd.DatetimeIndex(timestamps)
                ).sort_index()

                # Remove any duplicate timestamps
                price_series = price_series.groupby(level=0).last()

                if len(price_series) < 50:  # Still need minimum data after cleaning
                    data_length_stats.append(len(price_series))
                    continue

                # Track data length and time span for analysis
                data_length_stats.append(len(price_series))
                time_span_hours = (
                    price_series.index.max() - price_series.index.min()
                ).total_seconds() / 3600
                data_span_hours.append(time_span_hours)

                # Apply all three measures
                # For MI: only include markets with at least 14 days for consistent corpus across all lags
                if time_span_hours >= _horizon_to_hours("14d"):  # 336 hours
                    mi_result = calculate_mutual_information_decay(price_series)
                else:
                    mi_result = {"lags": [], "mi_values": [], "half_life": None}

                acf_result = calculate_autocorrelation_half_life(price_series)
                wavelet_result = calculate_wavelet_variance(price_series)

                results.append(
                    {
                        "event_id": event.id,
                        "market_id": market.id,
                        "event_title": event.title[:50] + "..."
                        if len(event.title) > 50
                        else event.title,
                        "market_question": getattr(market, "question", "")[:100],
                        "price_points": len(price_series),
                        "time_span_hours": (
                            price_series.index.max() - price_series.index.min()
                        ).total_seconds()
                        / 3600,
                        # Mutual Information results
                        "mi_half_life": mi_result.get("half_life"),
                        "mi_max_value": max(mi_result.get("mi_values", [0]))
                        if mi_result.get("mi_values")
                        else 0,
                        "mi_decay_rate": (
                            mi_result.get("mi_values", [0])[0]
                            - mi_result.get("mi_values", [0])[-1]
                        )
                        / len(mi_result.get("mi_values", []))
                        if len(mi_result.get("mi_values", [])) > 1
                        else 0,
                        # Autocorrelation results
                        "acf_zero_crossing": acf_result.get("acf_zero_crossing"),
                        "ar1_half_life": acf_result.get("ar1_half_life"),
                        "acf_first_value": acf_result.get("acf_values", [0])[0]
                        if acf_result.get("acf_values")
                        else 0,
                        # Wavelet results
                        "wavelet_elbow_scale": wavelet_result["elbow_scale"],
                        "wavelet_max_variance": max(wavelet_result["variances"])
                        if wavelet_result["variances"]
                        else 0,
                        "wavelet_total_horizons": len(wavelet_result["horizons"]),
                        # Store full results for detailed analysis
                        "mi_full_result": mi_result,
                        "acf_full_result": acf_result,
                        "wavelet_full_result": wavelet_result,
                    }
                )

            except Exception as e:
                raise e
                logger.warning(f"Failed to analyze market {market.id}: {e}")
                continue

    # Log data length and span statistics
    if data_length_stats:
        data_stats = pd.Series(data_length_stats)
        span_stats = pd.Series(data_span_hours)

        logger.info("Market data length statistics:")
        logger.info(f"  Total markets examined: {len(data_stats)}")
        logger.info(f"  Min points: {data_stats.min()}")
        logger.info(f"  Max points: {data_stats.max()}")
        logger.info(f"  Mean points: {data_stats.mean():.1f}")
        logger.info(f"  Median points: {data_stats.median():.1f}")
        logger.info(f"  Q25: {data_stats.quantile(0.25):.1f}")
        logger.info(f"  Q75: {data_stats.quantile(0.75):.1f}")

        logger.info("Market data time span statistics (hours):")
        logger.info(
            f"  Min span: {span_stats.min():.1f}h ({span_stats.min() / 24:.1f} days)"
        )
        logger.info(
            f"  Max span: {span_stats.max():.1f}h ({span_stats.max() / 24:.1f} days)"
        )
        logger.info(
            f"  Mean span: {span_stats.mean():.1f}h ({span_stats.mean() / 24:.1f} days)"
        )
        logger.info(
            f"  Median span: {span_stats.median():.1f}h ({span_stats.median() / 24:.1f} days)"
        )
        logger.info(
            f"  Q25 span: {span_stats.quantile(0.25):.1f}h ({span_stats.quantile(0.25) / 24:.1f} days)"
        )
        logger.info(
            f"  Q75 span: {span_stats.quantile(0.75):.1f}h ({span_stats.quantile(0.75) / 24:.1f} days)"
        )

        # Check coverage for different horizons
        for horizon in ["14d", "30d"]:
            horizon_hours = _horizon_to_hours(horizon)
            count = (span_stats >= horizon_hours).sum()
            logger.info(
                f"  Markets with ≥{horizon_hours}h span (for {horizon} analysis): {count} ({count / len(span_stats) * 100:.1f}%)"
            )

        max_horizon_hours = _get_max_horizon_hours()
        min_data_points_for_max = max_horizon_hours * 2
        logger.info(
            f"  Markets with >{min_data_points_for_max} points (needed for {max_horizon_hours}h horizon): {(data_stats >= min_data_points_for_max).sum()}"
        )
        logger.info(f"  Markets with >1000 points: {(data_stats > 1000).sum()}")
        logger.info(f"  Markets with >2000 points: {(data_stats > 2000).sum()}")
        logger.info(f"  Markets analyzed (passed filtering): {len(results)}")

    return pd.DataFrame(results)


def create_volatility_analysis_plots(
    volatility_df: pd.DataFrame,
) -> None:
    """
    Create and export visualization plots for volatility measure analysis.
    """
    if volatility_df.empty:
        return

    # 1. Distribution of half-lives across measures
    half_life_data = []
    for _, row in volatility_df.iterrows():
        if row["mi_half_life"] is not None:
            half_life_data.append(
                {
                    "measure": "Mutual Information",
                    "half_life": row["mi_half_life"],
                    "market_id": row["market_id"],
                }
            )
        if (
            row["ar1_half_life"] is not None and row["ar1_half_life"] < 1000
        ):  # Filter extreme values
            half_life_data.append(
                {
                    "measure": "AR(1) Model",
                    "half_life": row["ar1_half_life"],
                    "market_id": row["market_id"],
                }
            )
        if row["acf_zero_crossing"] is not None:
            half_life_data.append(
                {
                    "measure": "ACF Zero Crossing",
                    "half_life": row["acf_zero_crossing"],
                    "market_id": row["market_id"],
                }
            )

    if half_life_data:
        half_life_df = pd.DataFrame(half_life_data)
        fig1 = px.box(
            half_life_df,
            x="measure",
            y="half_life",
            labels={"half_life": "Half-Life (hours)", "measure": "Volatility Measure"},
        )
        fig1.update_yaxes(type="log")
        apply_template(fig1)

        # Export directly
        slug = "distribution_of_half_lives_across_volatility_measures"
        export_figure(fig1, slug)

    # 2. Aggregated Mutual Information decay curve
    # Collect all MI results and aggregate by lag
    all_mi_data = []
    for _, row in volatility_df.iterrows():
        mi_result = row["mi_full_result"]
        if mi_result and mi_result.get("lags") and mi_result.get("mi_values"):
            for lag, mi_val in zip(mi_result["lags"], mi_result["mi_values"]):
                all_mi_data.append({"lag": lag, "mi_value": mi_val})

    if all_mi_data:
        mi_agg_df = pd.DataFrame(all_mi_data)
        # Aggregate by lag: compute mean and std
        mi_stats = (
            mi_agg_df.groupby("lag")
            .agg({"mi_value": ["mean", "std", "count"]})
            .round(6)
        )
        mi_stats.columns = ["mean_mi", "std_mi", "count"]
        mi_stats = mi_stats.reset_index()
        mi_stats = mi_stats[
            mi_stats["count"] >= 5
        ]  # Only lags with at least 5 observations for stable estimates

        # Apply rolling average smoothing for lags above 12 hours to reduce noise
        smoothed_mi = mi_stats["mean_mi"].copy()
        long_lag_mask = mi_stats["lag"] > 12
        if long_lag_mask.sum() > 2:  # Need at least 3 points for rolling average
            window_size = min(3, long_lag_mask.sum())
            smoothed_mi.loc[long_lag_mask] = (
                mi_stats.loc[long_lag_mask, "mean_mi"]
                .rolling(window=window_size, center=True, min_periods=1)
                .mean()
            )
        mi_stats["mean_mi"] = smoothed_mi

        fig2 = go.Figure()

        # Add mean line
        fig2.add_trace(
            go.Scatter(
                x=mi_stats["lag"],
                y=mi_stats["mean_mi"],
                mode="lines+markers",
                line=dict(width=3, color="blue"),
            )
        )

        # Create enhanced tick labels that show hours with horizon labels when available
        horizon_hours_map = {_horizon_to_hours(h): h for h in HORIZONS}

        # Get default tick values from plotly
        tick_vals = []
        tick_texts = []

        # Create ticks at nice intervals and at horizon boundaries
        max_lag = int(mi_stats["lag"].max())
        horizon_hours = [
            _horizon_to_hours(h) for h in HORIZONS if _horizon_to_hours(h) <= max_lag
        ]

        # Combine nice intervals with horizon hours (up to 14d)
        nice_intervals = [1, 6, 12, 24, 48, 96, 168, 336]
        horizon_hours_filtered = horizon_hours  # Include all horizon hours
        all_ticks = sorted(set(nice_intervals + horizon_hours_filtered))
        all_ticks = [t for t in all_ticks if t <= max_lag]

        for hours in all_ticks:
            tick_vals.append(hours)
            if hours in horizon_hours_map:
                tick_texts.append(f"{hours} ({horizon_hours_map[hours]})")
            else:
                tick_texts.append(str(hours))

        fig2.update_layout(
            xaxis_title="Lag (hours)",
            yaxis_title="Mutual Information (bits)",
            height=600,
            xaxis=dict(
                type="log", tickmode="array", tickvals=tick_vals, ticktext=tick_texts
            ),
            showlegend=False,
        )
        apply_template(fig2)

        # Export
        export_figure(fig2, "mutual_information_decay_curves")

    # 3. Aggregated Autocorrelation function
    # Collect all ACF results and aggregate by lag
    all_acf_data = []
    for _, row in volatility_df.iterrows():
        acf_result = row["acf_full_result"]
        if acf_result and acf_result.get("lags") and acf_result.get("acf_values"):
            for lag, acf_val in zip(acf_result["lags"], acf_result["acf_values"]):
                all_acf_data.append({"lag": lag, "acf_value": acf_val})

    if all_acf_data:
        acf_agg_df = pd.DataFrame(all_acf_data)
        # Aggregate by lag: compute mean and std
        acf_stats = (
            acf_agg_df.groupby("lag")
            .agg({"acf_value": ["mean", "std", "count"]})
            .round(6)
        )
        acf_stats.columns = ["mean_acf", "std_acf", "count"]
        acf_stats = acf_stats.reset_index()
        acf_stats = acf_stats[
            acf_stats["count"] >= 10
        ]  # Only lags with at least 10 observations for stable estimates

        fig3 = go.Figure()

        # Add mean line
        fig3.add_trace(
            go.Scatter(
                x=acf_stats["lag"],
                y=acf_stats["mean_acf"],
                mode="lines+markers",
                name="Mean ACF",
                line=dict(width=3, color="green"),
            )
        )

        # Add error bands
        if acf_stats["std_acf"].notna().any():
            fig3.add_trace(
                go.Scatter(
                    x=list(acf_stats["lag"]) + list(acf_stats["lag"][::-1]),
                    y=list(acf_stats["mean_acf"] + acf_stats["std_acf"])
                    + list((acf_stats["mean_acf"] - acf_stats["std_acf"])[::-1]),
                    fill="toself",
                    fillcolor="rgba(100,255,150,0.2)",
                    line=dict(color="rgba(255,255,255,0)"),
                    name="±1 Std Dev",
                    showlegend=True,
                )
            )

        # Add zero line for reference
        fig3.add_hline(
            y=0, line_dash="dash", line_color="red", annotation_text="Zero correlation"
        )

        fig3.update_layout(
            xaxis_title="Lag (hours)",
            yaxis_title="Autocorrelation Coefficient",
            height=600,
        )
        apply_template(fig3)

        # Export
        export_figure(fig3, "autocorrelation_functions")

    # 4. Aggregated Wavelet variance by horizon
    # Collect all wavelet results and aggregate by horizon
    all_wavelet_data = []
    for _, row in volatility_df.iterrows():
        wavelet_result = row["wavelet_full_result"]
        if (
            wavelet_result
            and wavelet_result.get("horizons")
            and wavelet_result.get("variances")
        ):
            for horizon, variance in zip(
                wavelet_result["horizons"], wavelet_result["variances"]
            ):
                all_wavelet_data.append({"horizon": horizon, "variance": variance})

    if all_wavelet_data:
        wavelet_agg_df = pd.DataFrame(all_wavelet_data)
        # Aggregate by horizon: compute mean and std
        wavelet_stats = (
            wavelet_agg_df.groupby("horizon")
            .agg({"variance": ["mean", "std", "count"]})
            .round(8)
        )
        wavelet_stats.columns = ["mean_variance", "std_variance", "count"]
        wavelet_stats = wavelet_stats.reset_index()
        wavelet_stats = wavelet_stats[
            wavelet_stats["count"] >= 5
        ]  # Only horizons with at least N observations

        # Sort horizons in logical order
        wavelet_stats = wavelet_stats.sort_values("horizon")

        fig4 = go.Figure()

        # Add mean line
        fig4.add_trace(
            go.Scatter(
                x=wavelet_stats["horizon"],
                y=wavelet_stats["mean_variance"],
                mode="lines+markers",
                name="Mean Wavelet Variance",
                line=dict(width=3, color="purple"),
            )
        )

        # Add error bands
        if wavelet_stats["std_variance"].notna().any():
            upper_bound = wavelet_stats["mean_variance"] + wavelet_stats["std_variance"]
            lower_bound = wavelet_stats["mean_variance"] - wavelet_stats["std_variance"]
            # Ensure lower bound is positive for log scale
            lower_bound = np.maximum(lower_bound, wavelet_stats["mean_variance"] * 0.01)

            fig4.add_trace(
                go.Scatter(
                    x=list(wavelet_stats["horizon"])
                    + list(wavelet_stats["horizon"][::-1]),
                    y=list(upper_bound) + list(lower_bound[::-1]),
                    fill="toself",
                    fillcolor="rgba(150,100,255,0.2)",
                    line=dict(color="rgba(255,255,255,0)"),
                    name="±1 Std Dev",
                    showlegend=True,
                )
            )

        fig4.update_layout(
            xaxis_title="Time Horizon",
            yaxis_title="Wavelet Variance (log scale)",
            yaxis_type="log",
            height=600,
        )
        apply_template(fig4)

        # Export
        export_figure(fig4, "wavelet_variance_by_horizon")

    # 5. Summary statistics comparison
    # Debug logging for summary statistics
    logger.debug("Creating summary statistics for volatility measures:")
    for col in [
        "mi_half_life",
        "ar1_half_life",
        "acf_zero_crossing",
        "wavelet_elbow_scale",
    ]:
        valid_count = volatility_df[col].notna().sum()
        logger.debug(f"  {col}: {valid_count} valid values")

    summary_data = {
        "Measure": [
            "MI Half-Life",
            "AR(1) Half-Life",
            "ACF Zero-Cross",
            "Wavelet Elbow",
        ],
        "Mean": [
            volatility_df["mi_half_life"].mean()
            if volatility_df["mi_half_life"].notna().sum() > 0
            else 0,
            volatility_df["ar1_half_life"].mean()
            if volatility_df["ar1_half_life"].notna().sum() > 0
            else 0,
            volatility_df["acf_zero_crossing"].mean()
            if volatility_df["acf_zero_crossing"].notna().sum() > 0
            else 0,
            volatility_df["wavelet_elbow_scale"].mean()
            if volatility_df["wavelet_elbow_scale"].notna().sum() > 0
            else 0,
        ],
        "Median": [
            volatility_df["mi_half_life"].median()
            if volatility_df["mi_half_life"].notna().sum() > 0
            else 0,
            volatility_df["ar1_half_life"].median()
            if volatility_df["ar1_half_life"].notna().sum() > 0
            else 0,
            volatility_df["acf_zero_crossing"].median()
            if volatility_df["acf_zero_crossing"].notna().sum() > 0
            else 0,
            volatility_df["wavelet_elbow_scale"].median()
            if volatility_df["wavelet_elbow_scale"].notna().sum() > 0
            else 0,
        ],
        "Valid_Count": [
            volatility_df["mi_half_life"].notna().sum(),
            volatility_df["ar1_half_life"].notna().sum(),
            volatility_df["acf_zero_crossing"].notna().sum(),
            volatility_df["wavelet_elbow_scale"].notna().sum(),
        ],
    }

    summary_df = pd.DataFrame(summary_data)
    fig5 = px.bar(
        summary_df,
        x="Measure",
        y="Median",
        hover_data=["Mean", "Valid_Count"],
        labels={"Measure": "Volatility Measure", "Median": "Median Half-Life (hours)"},
    )
    apply_template(fig5)

    # Export
    slug = "median_half_life_characteristic_scales_across_measures"
    export_figure(fig5, slug)


def create_brier_score_analysis_plots(df: pd.DataFrame) -> None:
    """
    Create and export visualization plots for Brier score analysis.
    """

    # 1. Main plot: Brier score vs time to event end (log scale)
    # Group by time bins and calculate average Brier score
    df_copy = df.copy()

    # Create logarithmic time bins
    df_copy["log_hours"] = np.log10(df_copy["hours_to_end"].clip(lower=0.1))
    df_copy["time_bin"] = pd.cut(df_copy["log_hours"], bins=50)

    # Calculate statistics per bin
    bin_stats = (
        df_copy.groupby("time_bin", observed=False)
        .agg({"brier_score": ["mean", "std", "count"], "hours_to_end": "mean"})
        .round(4)
    )

    bin_stats.columns = ["mean_brier", "std_brier", "count", "mean_hours"]
    bin_stats = bin_stats.reset_index()
    bin_stats = bin_stats[
        bin_stats["count"] >= 5
    ]  # Only bins with at least 5 observations

    # Median barplot for specific horizons
    # Define horizon labels and corresponding hour cutoffs
    horizon_labels = [
        "1h",
        "6h",
        "12h",
        "1d",
        "2d",
        "4d",
        "7d",
        "14d",
        "30d",
    ]
    horizon_hours = [
        1,
        6,
        12,
        24,
        48,
        96,
        168,
        336,
        720,
    ]

    # Keep observations up to the largest horizon only
    df_h = df_copy[df_copy["hours_to_end"] <= max(horizon_hours)].copy()

    # Build bins [0,1], (1,6], ... using the hour cutoffs; label with provided strings
    bins = [0] + horizon_hours
    df_h["horizon_bin"] = pd.cut(
        df_h["hours_to_end"], bins=bins, labels=horizon_labels, include_lowest=True
    )

    # Compute median brier score and counts per horizon label
    med_stats = (
        df_h.groupby("horizon_bin", observed=False)
        .agg(median_brier=("brier_score", "median"), count=("brier_score", "size"))
        .reset_index()
    )

    # Ensure all horizons appear in order, even if empty
    med_stats["horizon_bin"] = pd.Categorical(
        med_stats["horizon_bin"], categories=horizon_labels, ordered=True
    )
    med_stats = med_stats.sort_values("horizon_bin")

    # Barplot of medians
    subplot_fig = px.bar(
        med_stats,
        x="horizon_bin",
        y="median_brier",
        labels={
            "horizon_bin": "Time to Event End",
            "median_brier": "Median Sqrt-Brier Score",
        },
        hover_data={"count": True, "median_brier": ":.3f"},
    )

    # Move y-axis to the right side
    subplot_fig.update_yaxes(side="right")
    # Reverse the X-axis order so closer horizons appear on the right
    subplot_fig.update_xaxes(
        title_text="Time to Event End",
        categoryorder="array",
        categoryarray=list(reversed(horizon_labels)),
    )
    subplot_fig.update_yaxes(title_text="Median Error of Probability Estimate")

    # Apply theme
    apply_template(subplot_fig)
    subplot_fig.update_layout(
        width=800,
        height=600,
        margin=dict(t=50, b=50, l=50, r=100),
    )

    # Export
    slug = "brier_score_by_horizon"
    export_figure(subplot_fig, slug)

    # Volatility of market prices within each horizon interval (per-market)
    # For each market and horizon bin, compute the std of market_price values
    # in that window; then aggregate across markets using the median.
    df_vol = df_copy[df_copy["hours_to_end"] <= max(horizon_hours)].copy()
    bins = [0] + horizon_hours
    df_vol["horizon_bin"] = pd.cut(
        df_vol["hours_to_end"], bins=bins, labels=horizon_labels, include_lowest=True
    )

    per_market_vol = (
        df_vol.groupby(["event_id", "market_id", "horizon_bin"], observed=False)[
            "market_price"
        ]
        .agg(price_std="std", samples="size")
        .reset_index()
    )

    vol_stats = (
        per_market_vol.groupby("horizon_bin", observed=False)
        .agg(
            median_vol=("price_std", "median"),
            count=("price_std", lambda s: int(pd.Series(s).notna().sum())),
        )
        .reset_index()
    )

    vol_stats["horizon_bin"] = pd.Categorical(
        vol_stats["horizon_bin"], categories=horizon_labels, ordered=True
    )
    vol_stats = vol_stats.sort_values("horizon_bin")

    vol_fig = px.bar(
        vol_stats,
        x="horizon_bin",
        y="median_vol",
        labels={"horizon_bin": "Horizon", "median_vol": "Median Std of Price"},
        hover_data={"count": True, "median_vol": ":.4f"},
    )
    vol_fig.update_yaxes(side="right")
    vol_fig.update_xaxes(
        title_text="Time to Event End",
        categoryorder="array",
        categoryarray=list(reversed(horizon_labels)),
    )
    vol_fig.update_yaxes(title_text="Cross-event volatility of market price")
    apply_template(vol_fig)
    vol_fig.update_layout(
        width=800,
        height=600,
        margin=dict(t=50, b=50, l=50, r=100),
    )

    # Export
    slug = "volatility_of_market_prices_by_horizon"
    export_figure(vol_fig, slug)

    # 5. Event-specific Brier score trajectories
    if df_copy["event_id"].nunique() <= 10:  # Only show if not too many events
        fig5 = px.line(
            df_copy,
            x="hours_to_end",
            y="brier_score",
            color="event_title",
            log_x=True,
        )
        fig5.update_layout(
            xaxis_title="Hours to Event End",
            yaxis_title="Sqrt-Brier Score",
            height=600,
        )
        apply_template(fig5)

        # Export
        slug = "individual_event_sqrt_brier_trajectories"
        export_figure(fig5, slug)

    # Add one lightweight supplemental plot to maintain backward compatibility with tests
    # (not exported; only included in return value)
    fig_summary = px.histogram(df_copy, x="hours_to_end", nbins=30)
    # Reverse X so that 0 hours is on the right; move Y axis to the right
    fig_summary.update_xaxes(autorange="reversed", title_text="Hours to Event End")
    fig_summary.update_yaxes(side="right", title_text="Count of predictions")
    apply_template(fig_summary)

    # Export
    slug = "hours_to_end_distribution"
    export_figure(fig_summary, slug)


def load_full_market_data(events: list) -> dict:
    """Load full market data using the improved caching from long_time_series_request."""

    logger.info("Loading market data (with per-market caching)...")
    full_market_data = {}

    for event in tqdm(events):
        event_data = {}
        for market in event.markets:
            if (
                market.outcomes
                and len(market.outcomes) >= 1
                and market.outcomes[0].clob_token_id
            ):
                # Calculate start datetime: 90 days before event end to ensure sufficient data for 30d analysis
                end_dt = (
                    _to_utc(event.end_datetime)
                    if event.end_datetime
                    else datetime.now(timezone.utc)
                )
                start_dt = end_dt - timedelta(days=90)

                ts_request = _HistoricalTimeSeriesRequest(
                    clob_token_id=market.outcomes[0].clob_token_id,
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    fidelity=60,  # Hourly data
                    resample="1h",
                )

                try:
                    ts = ts_request.get_cached_token_timeseries(
                        start_datetime=start_dt,
                        end_datetime=end_dt,
                        fidelity=60,
                        resample="1h",
                    )
                    if ts is not None and not ts.empty:
                        # Convert to serializable format
                        market_data = {
                            "timestamps": [dt.isoformat() for dt in ts.index],
                            "values": [float(val) for val in ts.values],
                            "market_id": market.id,
                            "clob_token_id": market.outcomes[0].clob_token_id,
                        }
                        event_data[market.id] = market_data
                        logger.debug(f"Loaded {len(ts)} points for market {market.id}")
                except Exception as e:
                    logger.warning(f"Failed to load data for market {market.id}: {e}")
                    continue

        if event_data:
            full_market_data[event.id] = event_data

    return full_market_data


def main():
    """Main analysis function."""
    logger.info("Starting market probabilities Brier score evolution analysis...")

    # Load data components separately to avoid leaderboard issues
    logger.info("Loading events and market prices...")
    _saved_events = load_saved_events()
    events = get_non_duplicated_events(_saved_events)

    # Load full market data with improved per-market caching
    full_market_data = load_full_market_data(events)

    # Convert to backend events with cached prices
    backend_events = []
    for event in events:
        backend_event = EventBackend.from_event(event)
        included_markets = []

        if event.id in full_market_data:
            for market in backend_event.markets:
                if market.id in full_market_data[event.id]:
                    market_data = full_market_data[event.id][market.id]

                    market.prices = [
                        DataPoint(date=ts, value=val)
                        for ts, val in zip(
                            market_data["timestamps"], market_data["values"]
                        )
                    ]
                    logger.debug(
                        f"Loaded {len(market.prices)} cached price points for market {market.id}"
                    )
                    included_markets.append(market)

        # Only keep the event if it has at least one included market
        if included_markets:
            backend_event.markets = included_markets
            backend_events.append(backend_event)

    # Calculate Brier scores over time
    logger.info("Calculating time-to-event Brier scores...")
    brier_df = calculate_time_to_event_brier_scores(backend_events)

    if brier_df.empty:
        logger.error("No resolved events with price data found!")
        return

    logger.info(
        f"Processed {len(brier_df)} price observations from {brier_df['event_id'].nunique()} events"
    )

    # Analyze price volatility measures
    logger.info("Analyzing price volatility measures...")
    volatility_df = analyze_market_volatility_measures(backend_events)

    if not volatility_df.empty:
        logger.info(
            f"Analyzed volatility for {len(volatility_df)} markets from {volatility_df['event_id'].nunique()} events"
        )

        # Log summary statistics
        logger.info("Volatility Analysis Summary:")

        # Debug logging for MI half-life
        mi_values = volatility_df["mi_half_life"].dropna()
        logger.debug(
            f"MI half-life: {len(mi_values)} non-null values out of {len(volatility_df)}"
        )
        if len(mi_values) > 0:
            logger.info(f"  MI half-life (median): {mi_values.median():.2f}")
        else:
            logger.info("  MI half-life (median): No valid values")

        # Debug logging for AR(1) half-life
        ar1_values = volatility_df["ar1_half_life"].dropna()
        logger.debug(
            f"AR(1) half-life: {len(ar1_values)} non-null values out of {len(volatility_df)}"
        )
        if len(ar1_values) > 0:
            logger.info(f"  AR(1) half-life (median): {ar1_values.median():.2f}")
        else:
            logger.info("  AR(1) half-life (median): No valid values")

        # Debug logging for ACF zero-crossing
        acf_values = volatility_df["acf_zero_crossing"].dropna()
        logger.debug(
            f"ACF zero-crossing: {len(acf_values)} non-null values out of {len(volatility_df)}"
        )
        if len(acf_values) > 0:
            logger.info(f"  ACF zero-crossing (median): {acf_values.median():.2f}")
        else:
            logger.info("  ACF zero-crossing (median): No valid values")

        # Debug logging for Wavelet elbow scale
        wavelet_values = volatility_df["wavelet_elbow_scale"].dropna()
        logger.debug(
            f"Wavelet elbow scale: {len(wavelet_values)} non-null values out of {len(volatility_df)}"
        )
        if len(wavelet_values) > 0:
            logger.info(
                f"  Wavelet elbow scale (median): {wavelet_values.median():.2f}"
            )
        else:
            logger.info("  Wavelet elbow scale (median): No valid values")
    else:
        logger.warning("No markets had sufficient data for volatility analysis")

    # Create and export visualizations
    logger.info("Creating and exporting visualizations...")

    # Export each figure individually with proper names
    create_brier_score_analysis_plots(brier_df)
    if not volatility_df.empty:
        create_volatility_analysis_plots(volatility_df)

    # Save summary statistics
    summary_stats = {
        "total_observations": len(brier_df),
        "unique_events": brier_df["event_id"].nunique(),
        "avg_brier_score": brier_df["brier_score"].mean(),
        "std_brier_score": brier_df["brier_score"].std(),
        "time_range_hours": (
            brier_df["hours_to_end"].min(),
            brier_df["hours_to_end"].max(),
        ),
    }

    logger.info("Analysis Summary:")
    for key, value in summary_stats.items():
        logger.info(f"  {key}: {value}")

    logger.info("Market probabilities Brier score evolution analysis completed!")


if __name__ == "__main__":
    main()
