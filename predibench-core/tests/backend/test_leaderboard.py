import pytest
from predibench.backend.leaderboard import get_leaderboard
from predibench.backend.data_loader import load_investment_choices_from_google, load_saved_events, load_agent_position, load_market_prices
from predibench.backend.pnl import get_historical_returns


def test_get_leaderboard():
    """End-to-end test that get_leaderboard returns a list of leaderboard entries"""
    # Load real data
    model_results = load_investment_choices_from_google()
    saved_events = load_saved_events()
    positions_df = load_agent_position(model_results)
    market_prices = load_market_prices(saved_events)
    prices_df = get_historical_returns(market_prices)
    
    assert len(market_prices) > 80
    assert len(positions_df) > 30
    
    # Test the leaderboard function
    result = get_leaderboard(positions_df, prices_df)
    assert isinstance(result, list)
    if result:
        assert hasattr(result[0], 'final_cumulative_pnl')
        
        
if __name__ == "__main__":
    test_get_leaderboard()