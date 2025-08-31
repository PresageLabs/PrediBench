from predibench.backend.data_loader import load_agent_choices, get_market_to_clob


def test_load_agent_choices():
    markets_to_grob = get_market_to_clob()
    assert len(markets_to_grob) > 80
    assert len(load_agent_choices()) > 30
    

    
if __name__ == "__main__":
    test_load_agent_choices()
    