import pytest
from predibench.backend.leaderboard import get_leaderboard
from predibench.backend.data_loader import load_investment_choices_from_google, load_saved_events, load_agent_position, load_market_prices
from predibench.backend.pnl import get_historical_returns
from predibench.backend.data_model import EventBackend
from predibench.backend.comprehensive_data import _compute_model_performance_list, _to_date_index


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
    
    # Build backend events and compute performance first, then leaderboard
    backend_events = [EventBackend.from_event(e) for e in saved_events]
    prices_df = _to_date_index(prices_df)
    performance = _compute_model_performance_list(positions_df, prices_df, backend_events)
    result = get_leaderboard(performance)
    assert isinstance(result, list)
    if result:
        assert hasattr(result[0], 'final_cumulative_pnl')
        
        
if __name__ == "__main__":
    test_get_leaderboard()
