import os
import pytest
from predibench.agent.smolagents_utils import GoogleSearchTool


def test_bright_data_forward():
    """Test Bright Data provider forward method."""
    
    # Create tool and test
    tool = GoogleSearchTool(provider="bright_data", cutoff_date=None)
    result = tool.forward("September 2025 Federal Reserve meeting expectations September 2025 rate cut probability")
    
    # Basic assertions
    assert isinstance(result, str)
    assert len(result) > 0
    print(f"Result: {result}")
    
def test_bright_data_2():
    import requests
    import json
    url = "https://api.brightdata.com/request"

    payload = {
        "method": "GET",
        "zone": "serp_api1",
        "url": "https://google.com/search?q=pizza&gl=US&hl=en&brd_json=1",
        "format": "json",
    }
    headers = {
        "Authorization": "Bearer 46536f1714a460eaf09bd68b4a344b88810168432875d300ebfed4e94fb51c76",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    result = response.json()
    body = json.loads(result["body"])
    pass


if __name__ == "__main__":
    test_bright_data_2()