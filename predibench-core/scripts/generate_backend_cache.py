#!/usr/bin/env python3
"""
Script to pre-compute and cache all backend data for maximum performance.

This script computes all data needed for the backend API endpoints and saves
it to storage using the storage utilities.
"""
import json
from pathlib import Path
from datetime import datetime

from predibench.backend.comprehensive_data import get_data_for_backend
from predibench.storage_utils import write_to_storage
from predibench.common import DATA_PATH


def main():
    """Main function to generate backend cache."""
    print("=== Backend Cache Generation ===")
    print(f"Started at: {datetime.now()}")
    
    # Compute all backend data
    print("\n1. Computing comprehensive backend data...")
    backend_data = get_data_for_backend()
    
    # Convert to JSON-serializable format
    print("\n2. Converting to JSON format...")
    backend_data_dict = backend_data.model_dump()
    json_content = json.dumps(backend_data_dict, indent=2, default=str)
    
    # Save using storage utilities
    cache_file_path = DATA_PATH / "backend_cache.json"
    print(f"\n3. Saving to storage...")
    write_to_storage(cache_file_path, json_content)
    
    # Print summary statistics
    print(f"\n=== Cache Generation Complete ===")
    print(f"Generated at: {datetime.now()}")
    
    print(f"\nData summary:")
    print(f"  - Leaderboard entries: {len(backend_data.leaderboard)}")
    print(f"  - Events: {len(backend_data.events)}")
    print(f"  - Model details: {len(backend_data.model_details)}")
    print(f"  - Model investment details: {len(backend_data.model_investment_details)}")
    print(f"  - Event details: {len(backend_data.event_details)}")
    print(f"  - Event market prices: {len(backend_data.event_market_prices)}")
    print(f"  - Event investment decisions: {len(backend_data.event_investment_decisions)}")
    
    print(f"\n✓ Backend cache saved successfully!")
    print(f"Cache location: backend_cache.json")


if __name__ == "__main__":
    main()