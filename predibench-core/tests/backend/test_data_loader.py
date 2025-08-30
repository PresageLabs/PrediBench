from predibench.backend.data_loader import load_agent_choices


def test_load_agent_choices():
    assert len(load_agent_choices()) > 30
    
    
if __name__ == "__main__":
    test_load_agent_choices()