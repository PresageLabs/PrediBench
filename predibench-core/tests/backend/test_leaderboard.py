import pytest
from predibench.backend.leaderboard import get_leaderboard


def test_get_leaderboard():
    """Test that get_leaderboard returns a list of leaderboard entries"""
    result = get_leaderboard()
    assert isinstance(result, list)
    if result:
        assert hasattr(result[0], 'final_cumulative_pnl')
        
        
if __name__ == "__main__":
    test_get_leaderboard()