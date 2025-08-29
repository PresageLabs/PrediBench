from dotenv import load_dotenv
from predibench.polymarket_api import convert_polymarket_time_to_datetime

load_dotenv()


def test_timestamp_extraction():
    """Test the timestamp extraction functionality from polymarket_api.py"""
    print("Testing timestamp extraction...")

    test_timestamps = [
        "2024-01-15T10:30:00Z",
        "2024-02-20T15:45:30.123Z",
        "2024-03-25T00:00:00Z",
    ]

    for ts_str in test_timestamps:
        dt = convert_polymarket_time_to_datetime(ts_str)
        print(f"  {ts_str} -> {dt}")

    print("Timestamp extraction test completed successfully!\n")


def test_structure_final_answer():
    research_output = """
So here are the investment decisions:
For the first one:
1. market_id (str): 1234
2. rationale (str): I think this market is grossly underpriced
3. odds (float, 0 to 1): 1
4. confidence (int, 0 to 10): 10
5. bet (float, -1 to 1): -1

Now the second one:
1. market_id (str): 4321
2. rationale (str): I think there's too much hype in the market
3. odds (float, 0 to 1): 0.25
4. confidence (int, 0 to 10): 3
5. bet (float, -1 to 1): -0.57

And a third
1. market_id (str): 3azdoi5
2. rationale (str): This is it.
3. odds (float, 0 to 1): 0.
4. confidence (int, 0 to 10): 0
5. bet (float, -1 to 1): -0.0
"""
    from predibench.agent.smolagents_utils import structure_final_answer

    list_decisions, unallocated_capital = structure_final_answer(research_output)

    first_decision = list_decisions[0]
    second_decision = list_decisions[1]
    third_decision = list_decisions[2]

    # Test that we got the correct number of decisions
    assert len(list_decisions) == 3

    # Test first decision
    assert first_decision.market_id == "1234"
    assert (
        first_decision.model_decision.rationale
        == "I think this market is grossly underpriced"
    )
    assert first_decision.model_decision.odds == 1.0
    assert first_decision.model_decision.confidence == 10
    assert first_decision.model_decision.bet == -1.0

    # Test second decision
    assert second_decision.market_id == "4321"
    assert (
        second_decision.model_decision.rationale
        == "I think there's too much hype in the market"
    )
    assert second_decision.model_decision.odds == 0.25
    assert second_decision.model_decision.confidence == 3
    assert second_decision.model_decision.bet == -0.57

    # Test third decision
    assert third_decision.market_id == "3azdoi5"
    assert third_decision.model_decision.rationale == "This is it."
    assert third_decision.model_decision.odds == 0.0
    assert third_decision.model_decision.confidence == 0
    assert third_decision.model_decision.bet == 0

    # Test unallocated capital is a float
    assert isinstance(unallocated_capital, float)

    print("test_structure_final_answer completed successfully!")
