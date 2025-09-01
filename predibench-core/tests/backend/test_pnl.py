import pytest
import pandas as pd
from datetime import date
import sys
import os


from predibench.backend.pnl import compute_pnl_per_model


def test_calculate_pnl_with_nans():
    """
    Test PnL calculation with realistic data including NaN values.
    
    Scenario:
    - 10 days of data
    - Agent starts betting on market_A from day 3, stops day 8
    - Agent bets on market_B from day 5 to day 10
    - Some prices have NaN (market not active)
    
    Expected behavior:
    - market_A: PnL calculated from day 3 (first bet) to day 8 (last price)
    - market_B: PnL calculated from day 5 (first bet) to day 10 (last price)
    """
    # 10 days of data
    dates = [date(2024, 1, i) for i in range(1, 11)]
    
    # Agent positions with NaN values
    positions_df = pd.DataFrame({
        'market_A': [None, None, 100.0, None, 150.0, None, 100.0, 50.0, None, None],
        'market_B': [None, None, None, None, 200.0, 200.0, 200.0, 150.0, 100.0, 100.0]
    }, index=dates)
    
    # Market prices with NaN (markets not active on some days)
    prices_df = pd.DataFrame({
        'market_A': [None, 0.2, 0.50, None, 0.52, 0.58, 0.60, 0.62, 1.0, 1.0],
        'market_B': [None, None, None, None, 0.30, 0.32, 0.28, 0.35, 0.38, 0.36]
    }, index=dates)
    
    result = compute_pnl_per_model(positions_df, prices_df)
    
    # Manual calculation with new realistic data (with price interpolation and position forward-filling):
    # market_A (days 3-10, with position forward-filling):
    # Original positions: Day3=100, Day4=None, Day5=150, Day6=None, Day7=100, Day8=50, Day9=None, Day10=None
    # Forward-filled positions: Day3=100, Day4=100(ffill), Day5=150, Day6=150(ffill), Day7=100, Day8=50, Day9=50(ffill), Day10=50(ffill)
    # Prices: Day3=0.50, Day4=0.51(interpolated), Day5=0.52, Day6=0.58, Day7=0.60, Day8=0.62, Day9=1.0, Day10=1.0
    # Day 3: $0 (first day)
    # Day 4: 100 × (0.51-0.50) = $1, cumulative = $1
    # Day 5: 100 × (0.52-0.51) = $1, cumulative = $2  (held position from day 4)
    # Day 6: 150 × (0.58-0.52) = $9, cumulative = $11
    # Day 7: 150 × (0.60-0.58) = $3, cumulative = $14 (held position from day 6)
    # Day 8: 100 × (0.62-0.60) = $2, cumulative = $16
    # Day 9: 50 × (1.0-0.62) = $19, cumulative = $35
    # Day 10: 50 × (1.0-1.0) = $0, cumulative = $35 (held position from day 9)
    
    # market_B (days 5-10):
    # Day 5: $0 (first day)
    # Day 6: 200 × (0.32-0.30) = $4, cumulative = $4
    # Day 7: 200 × (0.28-0.32) = -$8, cumulative = -$4
    # Day 8: 200 × (0.35-0.28) = $14, cumulative = $10
    # Day 9: 150 × (0.38-0.35) = $4.5, cumulative = $14.5
    # Day 10: 100 × (0.36-0.38) = -$2, cumulative = $12.5
    
    # Total expected: $35 + $12.5 = $47.5
    
    assert abs(result.final_pnl - 47.5) < 0.01  # Allow for floating point precision
    
    # Verify that sum of market PnLs equals total cumulative PnL
    for total_point in result.cumulative_pnl:
        date_str = total_point.date
        total_pnl = total_point.value
        
        # Sum market PnLs for this date
        market_sum = 0.0
        for market_points in result.market_pnls.values():
            # Find the point for this date in each market
            market_point = next((p for p in market_points if p.date == date_str), None)
            if market_point:
                market_sum += market_point.pnl
        
        # Check they match (within floating point precision)
        assert abs(total_pnl - market_sum) < 0.01, f"Day {date_str}: Total PnL ${total_pnl:.2f} != Sum of markets ${market_sum:.2f}"
    
    print(f"✓ Test passed: Final PnL = ${result.final_pnl}")
    print("✓ Sum validation passed: Market PnLs sum to total PnL")
    print("Daily progression:")
    for point in result.cumulative_pnl:
        print(f"  {point.date}: ${point.value}")


if __name__ == "__main__":
    test_calculate_pnl_with_nans()