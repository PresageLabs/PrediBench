#!/usr/bin/env python3
"""
Price variation study for a specific Polymarket event.

This script fetches 10-minute price data for the Polymarket event:
  https://polymarket.com/event/new-york-city-mayoral-election?tid=1758290937964

It focuses on the time window June 24–26, 2025 (UTC), visualizes the price
evolution, applies the project plotting template, and exports the figure to:
  analyses/market_variation/sudden_change.html

Notes:
- Uses EventsRequestParameters to fetch the event by slug and extracts the
  first outcome's token for price history at 10-minute resolution.
- Requires network access to Polymarket APIs on first run (cached thereafter).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
from predibench.logger_config import get_logger
from predibench.utils import apply_template
from pydantic import BaseModel

logger = get_logger(__name__)


def _get_event_json_by_slug(slug: str) -> dict:
    url = f"https://gamma-api.polymarket.com/events/slug/{slug}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _select_market_for_candidate(event_json: dict, keywords: list[str]) -> dict:
    """Return the market JSON object matching candidate keywords.

    Filters markets whose question/title contains any of the keywords (case-insensitive).
    """
    markets = event_json.get("markets", [])
    kw_lower = [k.lower() for k in keywords]

    def matches_candidate(q: str) -> bool:
        ql = (q or "").lower()
        return any(k in ql for k in kw_lower)

    candidate_markets = [
        m
        for m in markets
        if matches_candidate(m.get("question") or m.get("title") or "")
    ]
    if not candidate_markets:
        raise RuntimeError("No markets matched candidate keywords")
    # Return the first by default (these events often have one market per candidate)
    return candidate_markets[0]


class _HistoricalTimeSeriesRequest(BaseModel):
    clob_token_id: str
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    cache_results: bool = True
    resample: str | timedelta | None = "1D"
    fidelity: int | None = None
    url: str | None = None
    update_cache: bool = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        assert self.clob_token_id is not None
        self.url = "https://clob.polymarket.com/prices-history"

    def get_token_daily_timeseries(
        self,
        start_datetime: datetime | None = None,
        end_datetime: datetime | None = None,
        fidelity: int | None = None,
        resample: str | timedelta | None = None,
    ) -> pd.Series[datetime, float]:
        """Make a single API request for timeseries data."""
        effective_start_datetime = start_datetime or self.start_datetime
        effective_end_datetime = end_datetime or self.end_datetime
        effective_fidelity = fidelity or self.fidelity
        effective_resample = resample or self.resample
        assert (
            effective_start_datetime is not None and effective_end_datetime is not None
        ), "Need to specify start and end datetime"

        # Normalize to timezone-aware UTC
        effective_start_datetime = effective_start_datetime.astimezone(timezone.utc)
        effective_end_datetime = effective_end_datetime.astimezone(timezone.utc)

        # If too long, split into several
        if effective_end_datetime - effective_start_datetime > timedelta(
            days=14, hours=23, minutes=0
        ):
            start_datetimes = [
                dt.to_pydatetime()
                for dt in pd.date_range(
                    start=effective_start_datetime,
                    end=effective_end_datetime,
                    freq=timedelta(days=14, hours=23, minutes=0),
                )
            ]
            end_datetimes = start_datetimes[1:] + [effective_end_datetime]
            all_timeseries = []
            for sub_start_datetime, sub_end_datetime in zip(
                start_datetimes, end_datetimes
            ):
                new_timeseries = self.get_token_daily_timeseries(
                    start_datetime=sub_start_datetime,
                    end_datetime=sub_end_datetime,
                    fidelity=effective_fidelity,
                    resample=effective_resample,
                )
                if len(new_timeseries) > 0:
                    all_timeseries.append(new_timeseries)
            timeseries = pd.concat(all_timeseries) if all_timeseries else pd.Series()

        else:
            start_ts = int(effective_start_datetime.timestamp())
            end_ts = int(effective_end_datetime.timestamp())
            set_of_params = [
                {
                    "market": self.clob_token_id,
                    "startTs": start_ts,
                    "endTs": end_ts,
                    "fidelity": str(effective_fidelity)
                    if effective_fidelity is not None
                    else None,
                },
                {
                    "market": self.clob_token_id,
                    "startTs": start_ts,
                    "endTs": end_ts,
                },
            ]
            for params in set_of_params:
                # Remove None values
                clean_params = {k: v for k, v in params.items() if v is not None}
                response = requests.get(self.url, params=clean_params)
                response.raise_for_status()
                data = response.json()
                if len(data["history"]) > 0:
                    break

            timeseries = pd.Series(
                [point["p"] for point in data["history"]],
                index=pd.to_datetime(
                    [
                        datetime.fromtimestamp(point["t"], tz=timezone.utc)
                        for point in data["history"]
                    ],
                    utc=True,
                ),
            ).sort_index()

        if effective_resample:
            timeseries = timeseries.resample(effective_resample).last()
        timeseries = timeseries.ffill()
        return timeseries

    def _fetch_and_cache_timeseries(
        self,
        start_datetime: datetime | None = None,
        end_datetime: datetime | None = None,
        fidelity: int | None = None,
        resample: str | timedelta | None = None,
    ) -> pd.Series | None:
        """Fetch timeseries data from API and cache it."""
        merged_data = self.get_token_daily_timeseries(
            fidelity=self.fidelity or fidelity,
            resample=self.resample or resample,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        )

        return merged_data

    def _check_if_market_closed(self, timeseries: pd.Series) -> bool:
        """Check if market is closed based on last price."""
        if timeseries is None or len(timeseries) == 0:
            return True

        # Get the most recent timestamp
        last_timestamp = timeseries.index.max()

        # Ensure timezone awareness
        if hasattr(last_timestamp, "tzinfo") and last_timestamp.tzinfo is None:
            last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)

        # Check if last price is older than 12 hours
        two_days_ago = datetime.now(timezone.utc) - timedelta(hours=12)
        return last_timestamp < two_days_ago


def main():
    # Config
    # Event slug provided
    slug = "new-york-city-mayoral-election"
    # Window in UTC
    start_utc = datetime(2025, 6, 24, 21, 0, 0, tzinfo=timezone.utc)
    end_utc = datetime(2025, 6, 25, 3, 0, 0, tzinfo=timezone.utc)

    logger.info("Fetching event JSON by slug via requests…")
    event_json = _get_event_json_by_slug(slug)
    market_json = _select_market_for_candidate(
        event_json, ["zohran", "mahmadi", "mamdani"]
    )
    market_question = (
        market_json.get("question") or market_json.get("title") or "(unknown)"
    )

    # Build identifier candidates: clob tokens (prefer YES if present), then market id

    outcomes = json.loads(market_json.get("outcomes") or "[]")
    token = json.loads(market_json.get("clobTokenIds") or "[]")[0]
    print(market_question, token, outcomes)

    full_ts = None
    id_candidates = [token]
    for id_candidate in id_candidates:
        req = _HistoricalTimeSeriesRequest(
            clob_token_id=id_candidate,
            start_datetime=start_utc,
            end_datetime=end_utc,
        )
        print(f"Fetching timeseries for {id_candidate}")
        ts = req.get_token_daily_timeseries(fidelity=1, resample="1min")
        if ts is not None and not ts.empty:
            full_ts = ts
            break

    if full_ts is None:
        raise RuntimeError("No timeseries returned for any candidate identifier")

    # Slice to requested window
    # Ensure index is tz-aware UTC
    if full_ts.index.tz is None:
        full_ts.index = full_ts.index.tz_localize("UTC")
    window_ts = full_ts.loc[(full_ts.index >= start_utc) & (full_ts.index <= end_utc)]

    logger.info(
        f"Window points: {len(window_ts)} | Range: {window_ts.index.min()} → {window_ts.index.max()}"
    )

    # Build DataFrame for PX
    df = window_ts.rename("price").to_frame()
    df = df.reset_index().rename(columns={"index": "datetime"})

    fig = px.line(df, x="datetime", y="price", markers=True)
    fig.update_layout(xaxis_title="UTC time", yaxis_title="Price (Yes)")
    apply_template(fig)
    fig.update_layout(width=800, height=600)

    repo_root = Path(__file__).resolve().parents[3]
    out_dir = repo_root / "predibench-frontend-react/public/sudden_price_change"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = (out_dir / "nyc_election_mahmadi.json").resolve()
    fig.write_json(str(out_path))

    logger.info(f"Saved figure to: {out_path}")
    print(str(out_path))


if __name__ == "__main__":
    main()
