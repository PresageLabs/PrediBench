#!/usr/bin/env python3
"""
Script to update all markets that have cached files and are not closed.

This script will scan the timeseries_cache directory for existing cached markets
and update their timeseries data if they are not marked as closed.
"""

import json
from pathlib import Path

from predibench.storage_utils import get_bucket, has_bucket_read_access, read_from_storage
from predibench.logger_config import get_logger
from predibench.polymarket_api import _HistoricalTimeSeriesRequestParameters

logger = get_logger(__name__)


def list_cached_markets() -> list[str]:
    """
    List all clob_token_ids that have cached timeseries data in the bucket.
    
    Returns:
        List of clob_token_ids that have cached files
    """
    if not has_bucket_read_access():
        logger.error("No bucket read access available")
        return []
    
    bucket = get_bucket()
    if bucket is None:
        logger.error("Could not get bucket")
        return []
    
    # List all blobs in the timeseries_cache directory
    cache_prefix = "timeseries_cache/"
    blobs = bucket.list_blobs(prefix=cache_prefix)
    
    cached_markets = []
    
    for blob in blobs:
        # Extract clob_token_id from the blob name
        # Format: timeseries_cache/{clob_token_id}.json
        blob_path = Path(blob.name)
        if blob_path.suffix == ".json":
            clob_token_id = blob_path.stem
            cached_markets.append(clob_token_id)
            logger.info(f"Found cached data for token: {clob_token_id}")
    
    return cached_markets


def update_market(clob_token_id: str) -> bool:
    """
    Update a single market's cached timeseries data.
    
    Args:
        clob_token_id: The token ID to update
    
    Returns:
        True if successfully updated, False otherwise
    """
    ts_request = _HistoricalTimeSeriesRequestParameters(
        clob_token_id=clob_token_id,
        end_datetime=None  # Update to current time
    )
    
    # This will fetch fresh data and update the cache
    timeseries = ts_request.update_cached_token_timeseries()
    
    if timeseries is not None:
        logger.info(f"✅ Successfully updated market {clob_token_id}")
        return True
    else:
        logger.warning(f"⚠️ No timeseries data returned for market {clob_token_id}")
        return False


def main():
    """Main function to update all cached markets."""
    print("Scanning GCP bucket for cached timeseries data...")
    
    cached_markets = list_cached_markets()
    
    if not cached_markets:
        print("No cached markets found.")
        return
    
    print(f"Found {len(cached_markets)} cached markets")
    print(f"Updating markets (closed markets will be automatically skipped)...")
    print("-" * 80)
    
    successful_updates = 0
    failed_updates = 0
    
    for i, clob_token_id in enumerate(cached_markets, 1):
        print(f"[{i}/{len(cached_markets)}] Updating {clob_token_id}...")
        
        if update_market(clob_token_id):
            successful_updates += 1
        else:
            failed_updates += 1
    
    print("-" * 80)
    print(f"Update complete!")
    print(f"  ✅ Successfully updated: {successful_updates}")
    print(f"  ❌ Failed updates: {failed_updates}")
    print(f"  📊 Total markets processed: {len(cached_markets)}")


if __name__ == "__main__":
    main()