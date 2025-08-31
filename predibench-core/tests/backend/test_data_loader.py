from predibench.backend.data_loader import load_agent_position, load_market_prices


def test_load_agent_choices():
    market_prices = load_market_prices()
    assert len(market_prices) > 80
    assert len(load_agent_position()) > 30
    

    
if __name__ == "__main__":
    test_load_agent_choices()
    