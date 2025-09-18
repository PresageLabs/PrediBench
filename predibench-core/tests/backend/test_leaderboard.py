from predibench.backend.comprehensive_data import (
    _compute_profits,
    _to_date_index,
)
from predibench.backend.data_loader import (
    load_investment_choices_from_google,
    load_market_prices,
    load_saved_events,
)
from predibench.backend.leaderboard import get_leaderboard
from predibench.backend.pnl import get_market_prices_dataframe


def test_get_leaderboard():
    """End-to-end test that get_leaderboard returns a list of leaderboard entries"""
    # Load real data
    model_decisions = load_investment_choices_from_google()
    saved_events = load_saved_events()
    market_prices = load_market_prices(saved_events)
    prices_df = get_market_prices_dataframe(market_prices)

    assert len(market_prices) > 80

    # Build backend events and compute performance first, then leaderboard
    prices_df = _to_date_index(prices_df)
    model_decisions, performance_per_model = _compute_profits(
        prices_df=prices_df,
        model_decisions=model_decisions,
    )
    result = get_leaderboard(list(performance_per_model.values()))
    assert isinstance(result, list)
    if result:
        assert hasattr(result[0], "final_profit")


if __name__ == "__main__":
    test_get_leaderboard()
