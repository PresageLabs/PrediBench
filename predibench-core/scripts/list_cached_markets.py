#!/usr/bin/env python3
"""
Script to list all markets that have cached timeseries files in the GCP bucket.

This script will scan the timeseries_cache directory in the bucket and list all
clob_token_ids that have cached data available.
"""

import json
from pathlib import Path

from predibench.storage_utils import get_bucket, has_bucket_read_access
from predibench.logger_config import get_logger

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


def get_cached_market_info(clob_token_id: str) -> dict | None:
    """
    Get information about a cached market file.
    
    Args:
        clob_token_id: The token ID to get info for
    
    Returns:
        Dictionary with cache info or None if not found
    """
    if not has_bucket_read_access():
        return None
    
    bucket = get_bucket()
    if bucket is None:
        return None
    
    blob_name = f"timeseries_cache/{clob_token_id}.json"
    blob = bucket.blob(blob_name)
    
    if not blob.exists():
        return None
    
    try:
        # Get blob metadata
        blob.reload()
        
        # Download and parse the cached data to get additional info
        cached_data = json.loads(blob.download_as_text())
        
        return {
            "clob_token_id": clob_token_id,
            "file_size": blob.size,
            "last_modified": blob.updated.isoformat() if blob.updated else None,
            "data_points": len(cached_data.get("data", [])),
            "last_updated": cached_data.get("last_updated"),
            "date_range": {
                "start": cached_data["data"][0]["date"] if cached_data.get("data") else None,
                "end": cached_data["data"][-1]["date"] if cached_data.get("data") else None,
            }
        }
    except Exception as e:
        logger.error(f"Error getting info for {clob_token_id}: {e}")
        return {
            "clob_token_id": clob_token_id,
            "error": str(e)
        }


def main():
    """Main function to list all cached markets and their info."""
    print("Scanning GCP bucket for cached timeseries data...")
    
    cached_markets = list_cached_markets()
    
    if not cached_markets:
        print("No cached markets found.")
        return
    
    print(f"\nFound {len(cached_markets)} cached markets:")
    print("-" * 80)
    
    for clob_token_id in cached_markets:
        info = get_cached_market_info(clob_token_id)
        if info:
            if "error" in info:
                print(f"❌ {clob_token_id}: Error - {info['error']}")
            else:
                date_range = f"{info['date_range']['start']} to {info['date_range']['end']}"
                print(f"✅ {clob_token_id}:")
                print(f"   📊 {info['data_points']} data points")
                print(f"   📅 Date range: {date_range}")
                print(f"   💾 File size: {info['file_size']} bytes")
                print(f"   🕐 Last updated: {info['last_updated']}")
                print()
        else:
            print(f"❓ {clob_token_id}: Could not get info")
    
    print(f"\nTotal: {len(cached_markets)} cached markets")


if __name__ == "__main__":
    main()