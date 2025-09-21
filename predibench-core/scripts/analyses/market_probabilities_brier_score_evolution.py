#!/usr/bin/env python3
"""
Analysis of market probabilities Brier score evolution over time.

This script analyzes how the Brier scores of market predicted probabilities evolve
as a function of time to event end, showing market accuracy improvement over time.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from predibench.backend.data_loader import (
    load_market_prices,
    load_saved_events,
)
from predibench.backend.data_model import EventBackend
from predibench.backend.events import get_non_duplicated_events
from predibench.logger_config import get_logger
from predibench.polymarket_api import _HistoricalTimeSeriesRequestParameters
from predibench.utils import apply_template

logger = get_logger(__name__)

# Threshold to accept a market as clearly resolved at its stopping time
# We treat prices <= 0.05 as NO resolved, and >= 0.95 as YES resolved
EPSILON_TERMINAL = 0.05

# Outcome stats for logging/diagnostics
OUTCOME_STATS: dict[str, int] = {
    "eligible_markets": 0,  # markets with end passed and price data
    "resolved_markets": 0,  # markets that hit <=0.1 or >=0.9
    "dropped_unresolved_markets": 0,  # eligible but never hit thresholds
}


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


def _adjust_daily_points_to_end_of_day(
    ts: pd.Series, end_dt: datetime | None
) -> pd.Series:
    """
    Heuristic: daily-resampled points often carry midnight timestamps while representing
    end-of-day "last" values. Shift such timestamps to end-of-day to better align with
    the represented value timing, then clip to event end if provided.
    """
    if ts is None or len(ts) == 0:
        return ts
    idx = ts.index
    if not isinstance(idx, pd.DatetimeIndex):
        return ts
    # Identify midnight timestamps
    mask = (
        (idx.hour == 0) & (idx.minute == 0) & (idx.second == 0) & (idx.microsecond == 0)
    )
    if mask.any():
        shifted_idx = idx.copy()
        shifted_idx = shifted_idx.where(
            ~mask, shifted_idx + pd.Timedelta(hours=23, minutes=59)
        )
        ts = pd.Series(ts.values, index=shifted_idx).sort_index()
    # Clip to end_dt
    if end_dt is not None:
        ed = end_dt if end_dt.tzinfo else end_dt.replace(tzinfo=timezone.utc)
        ts = ts.loc[ts.index <= ed]
    return ts


def _to_utc(dt: datetime | None) -> datetime | None:
    """Ensure a datetime is timezone-aware in UTC."""
    if dt is None:
        return None
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


def get_granular_market_data(
    events: list[EventBackend], *, last_hours: int = 24
) -> dict:
    """
    Collect hourly market data for the last `last_hours` before event resolution.

    Args:
        events: List of events to process
        last_hours: Number of hours before event end to fetch at hourly granularity

    Returns:
        Dict mapping event_id -> market_id -> granular price series
    """
    granular_data = {}
    cache_per_market: dict[str, dict] = {}

    # Load existing cache if present to avoid redundant API calls
    cached_existing: dict[str, dict] = {}
    analyses_dir = Path("analyses")
    analyses_dir.mkdir(exist_ok=True)
    out_path = analyses_dir / "market_hourly_last24h_to_end.json"
    if out_path.exists():
        cached_existing = json.loads(out_path.read_text())

    for event in events:
        if event.end_datetime is None:
            continue
        # We want hourly data for the last `last_hours` before the event end
        if datetime.now(tz=timezone.utc) > (
            event.end_datetime.astimezone(timezone.utc)
            if event.end_datetime.tzinfo
            else event.end_datetime.replace(tzinfo=timezone.utc)
        ):
            logger.info(
                f"Collecting hourly data for last {last_hours}h before resolution for event {event.id}"
            )

            granular_data[event.id] = {}

            for market in event.markets:
                if len(market.outcomes) >= 1 and market.outcomes[0].clob_token_id:
                    # If already cached for this market, reuse cached series
                    if market.id in cached_existing:
                        entry = cached_existing[market.id]
                        # Ensure question is present for easier search
                        if "question" not in entry and getattr(
                            market, "question", None
                        ):
                            entry["question"] = market.question
                        end_dt = _parse_datetime_mixed(entry.get("end_datetime"))
                        # Recreate series
                        ser = pd.Series(
                            [pt["value"] for pt in entry.get("series", [])],
                            index=_parse_datetime_index_mixed(
                                [pt["datetime"] for pt in entry.get("series", [])]
                            ),
                        ).sort_index()
                        # Ensure slice covers last_hours to end_dt
                        start_dt = end_dt - timedelta(hours=last_hours)
                        ser = ser.loc[(ser.index > start_dt) & (ser.index <= end_dt)]
                        if not ser.empty:
                            granular_data[event.id][market.id] = ser
                            cache_per_market[market.id] = entry  # Keep in output cache
                            logger.info(
                                f"Using cached hourly slice for market {market.id} ({len(ser)} pts)"
                            )
                            continue

                    ts_request = _HistoricalTimeSeriesRequestParameters(
                        clob_token_id=market.outcomes[0].clob_token_id,
                        end_datetime=event.end_datetime,
                    )

                    # Fetch full hourly and 10-minute series up to event end
                    full_hourly = ts_request.get_token_daily_timeseries(
                        fidelity=60, resample="1h"
                    )
                    full_10min = ts_request.get_token_daily_timeseries(
                        fidelity=10, resample="10T"
                    )

                    if (full_hourly is None or full_hourly.empty) and (
                        full_10min is None or full_10min.empty
                    ):
                        continue

                        # Define the end datetime as the official event end (we detect effective end later)
                        end_dt = (
                            event.end_datetime.astimezone(timezone.utc)
                            if event.end_datetime.tzinfo
                            else event.end_datetime.replace(tzinfo=timezone.utc)
                        )

                    # Build combined series: hourly for (24h..6h], 10-min for (6h..0]
                    start_dt = end_dt - timedelta(hours=last_hours)
                    cutoff_10m = end_dt - timedelta(hours=6)
                    combined_parts = []
                    if full_hourly is not None and not full_hourly.empty:
                        hourly_slice = full_hourly.loc[
                            (full_hourly.index > start_dt)
                            & (full_hourly.index <= cutoff_10m)
                        ]
                        if not hourly_slice.empty:
                            combined_parts.append(hourly_slice)
                    if full_10min is not None and not full_10min.empty:
                        ten_slice = full_10min.loc[
                            (full_10min.index > cutoff_10m)
                            & (full_10min.index <= end_dt)
                        ]
                        if not ten_slice.empty:
                            combined_parts.append(ten_slice)

                    if not combined_parts:
                        # fallback: use any available hourly within 24h
                        if full_hourly is not None and not full_hourly.empty:
                            fallback = full_hourly.loc[
                                (full_hourly.index > start_dt)
                                & (full_hourly.index <= end_dt)
                            ]
                            if not fallback.empty:
                                combined_parts = [fallback]

                    if combined_parts:
                        combined_series = (
                            pd.concat(combined_parts)
                            .groupby(level=0)
                            .last()
                            .sort_index()
                        )
                        granular_data[event.id][market.id] = combined_series
                        logger.info(
                            f"Collected {len(combined_series)} points (hourly+10min) for market {market.id}"
                        )

                        # Populate cache structure keyed by market id with single merged series
                        cache_per_market[market.id] = {
                            "question": getattr(market, "question", None),
                            "end_datetime": end_dt.isoformat(),
                            "series": [
                                {
                                    "datetime": ts.isoformat(),
                                    "value": float(val),
                                }
                                for ts, val in combined_series.items()
                            ],
                        }

                    # else: if no combined parts, nothing to cache

    # Merge with existing cache and persist local JSON keyed by market id
    merged = {**cached_existing, **cache_per_market}
    with open(out_path, "w") as f:
        json.dump(merged, f, indent=2)
    logger.info(f"Saved hourly 24h-to-end cache to {out_path}")

    return granular_data


def create_brier_score_analysis_plots(df: pd.DataFrame) -> list[go.Figure]:
    """
    Create visualization plots for Brier score analysis.

    Returns:
        List of plotly figures
    """
    figures = []

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
        "3d",
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
        72,
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
        title="Median Sqrt-Brier Score by Horizon",
        labels={"horizon_bin": "Horizon", "median_brier": "Median Sqrt-Brier"},
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
    subplot_fig.update_yaxes(
        title_text="Market's predictions get more precise towards event end"
    )

    # Apply theme
    apply_template(subplot_fig)
    subplot_fig.update_layout(
        width=800,
        height=600,
        margin=dict(t=50, b=50, l=50, r=100),
    )
    figures.append(subplot_fig)

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
        title="Volatility of Market Prices by Horizon",
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
    figures.append(vol_fig)

    # 5. Event-specific Brier score trajectories
    if df_copy["event_id"].nunique() <= 10:  # Only show if not too many events
        fig5 = px.line(
            df_copy,
            x="hours_to_end",
            y="brier_score",
            color="event_title",
            title="Individual Event Sqrt-Brier Trajectories",
            log_x=True,
        )
        fig5.update_layout(
            xaxis_title="Hours to Event End",
            yaxis_title="Sqrt-Brier Score",
            height=600,
        )
        apply_template(fig5)
        figures.append(fig5)

    # Add one lightweight supplemental plot to maintain backward compatibility with tests
    # (not exported; only included in return value)
    fig_summary = px.histogram(
        df_copy, x="hours_to_end", nbins=30, title="Hours to End Distribution"
    )
    # Reverse X so that 0 hours is on the right; move Y axis to the right
    fig_summary.update_xaxes(autorange="reversed", title_text="Hours to Event End")
    fig_summary.update_yaxes(side="right", title_text="Count")
    apply_template(fig_summary)
    figures.append(fig_summary)

    return figures


def main():
    """Main analysis function."""
    logger.info("Starting market probabilities Brier score evolution analysis...")

    # Load data components separately to avoid leaderboard issues
    logger.info("Loading events and market prices...")
    _saved_events = load_saved_events()
    events = get_non_duplicated_events(_saved_events)
    market_prices = load_market_prices(events)

    # Convert to backend events with prices
    backend_events = []
    for event in events:
        backend_event = EventBackend.from_event(event)
        included_markets = []
        # Fill prices from higher-resolution cached timeseries; use daily map only to skip open markets
        for market in backend_event.markets:
            daily_market_data = market_prices.get(market.id)
            if daily_market_data is not None:
                # Skip markets that likely haven't finished yet: latest daily price < 1 day old
                last_idx_val = daily_market_data.index.max()
                # Convert to a pure date for robust comparison
                if isinstance(last_idx_val, pd.Timestamp):
                    last_date = last_idx_val.date()
                elif isinstance(last_idx_val, datetime):
                    last_date = last_idx_val.date()
                else:
                    last_date = pd.to_datetime(last_idx_val).date()
                today_date = datetime.now(timezone.utc).date()
                if (today_date - last_date) <= timedelta(days=1):
                    # Likely still open, skip this market to speed up
                    continue

            # Load cached datetime-indexed timeseries directly
            if (
                market.outcomes
                and len(market.outcomes) >= 1
                and market.outcomes[0].clob_token_id
            ):
                ts_request = _HistoricalTimeSeriesRequestParameters(
                    clob_token_id=market.outcomes[0].clob_token_id,
                    end_datetime=event.end_datetime,
                )
                ts = ts_request.get_cached_token_timeseries()
                if ts is None or ts.empty:
                    continue
                ts = _adjust_daily_points_to_end_of_day(ts, event.end_datetime)
                if ts is None or ts.empty:
                    continue
                from predibench.common_models import DataPoint

                market.prices = [
                    DataPoint(date=tsi.isoformat(), value=float(val))
                    for tsi, val in ts.items()
                ]
                included_markets.append(market)
        # Only keep the event if it has at least one included market
        if included_markets:
            backend_event.markets = included_markets
            backend_events.append(backend_event)

    # Collect granular data for events ending soon
    logger.info("Collecting hourly market data for last 24h before resolution...")
    granular_data = get_granular_market_data(backend_events, last_hours=24)

    # Enhance backend events with granular data
    for event in backend_events:
        if event.id in granular_data:
            for market in event.markets:
                if market.id in granular_data[event.id]:
                    granular_series = granular_data[event.id][market.id]
                    # Add granular data points to existing prices
                    from predibench.common_models import DataPoint

                    additional_prices = [
                        DataPoint(date=str(date), value=float(price))
                        for date, price in granular_series.items()
                    ]
                    if market.prices is None:
                        market.prices = additional_prices
                    else:
                        # Merge and sort by date
                        all_prices = market.prices + additional_prices
                        # Remove duplicates and sort
                        seen_dates = set()
                        unique_prices = []
                        for price_point in sorted(all_prices, key=lambda p: p.date):
                            if price_point.date not in seen_dates:
                                unique_prices.append(price_point)
                                seen_dates.add(price_point.date)
                        market.prices = unique_prices

    # Calculate Brier scores over time
    logger.info("Calculating time-to-event Brier scores...")
    brier_df = calculate_time_to_event_brier_scores(backend_events)

    if brier_df.empty:
        logger.error("No resolved events with price data found!")
        return

    logger.info(
        f"Processed {len(brier_df)} price observations from {brier_df['event_id'].nunique()} events"
    )

    # Create visualizations
    logger.info("Creating visualizations...")
    figures = create_brier_score_analysis_plots(brier_df)

    # Export all figures to dedicated subfolder under frontend public
    repo_root = Path(__file__).resolve().parents[3]
    base_dir = repo_root / "predibench-frontend-react/public/market_probabilities_brier_score_evolution"
    base_dir.mkdir(parents=True, exist_ok=True)

    def _slugify(title: str | None, fallback: str) -> str:
        if not title:
            return fallback
        s = title.lower().replace("—", "-").replace("–", "-")
        allowed = "abcdefghijklmnopqrstuvwxyz0123456789-_ "
        s = "".join(ch if ch in allowed else " " for ch in s)
        s = "_".join(part for part in s.split() if part)
        return s or fallback

    for i, fig in enumerate(figures, start=1):
        title_text = getattr(fig.layout, "title", None)
        title_text = getattr(title_text, "text", None) if title_text else None
        default_name = f"figure_{i:02d}"
        slug = _slugify(title_text, default_name)
        file_path = base_dir / f"{slug}.json"
        fig.write_json(str(file_path))
        logger.info(f"Saved plot to {file_path}")

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
