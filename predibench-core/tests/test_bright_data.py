import os
import pytest
from predibench.agent.smolagents_utils import GoogleSearchTool


def test_bright_data_forward():
    """Test Bright Data provider forward method."""
    
    # Create tool and test
    tool = GoogleSearchTool(provider="bright_data", cutoff_date=None)
    result = tool.forward("september 2025 federal reserve meeting expectations september 2025 rate cut probability")
    
    # Basic assertions
    assert isinstance(result, str)
    assert len(result) > 0
    assert "Search Results for" in result
    assert "september 2025 federal reserve" in result.lower()
    print(f"Result: {result}")
    
def test_bright_data():
    import requests
    import json
    from urllib.parse import urlencode
    url = "https://api.brightdata.com/request"

    # Define search parameters as dictionary
    search_params = {
        "q": "september 2025 federal reserve meeting expectations september 2025 rate cut probability",  # Example with spaces
        "gl": "US",
        "hl": "en",
        "brd_json": "1"
    }
    
    # Encode parameters properly
    encoded_params = urlencode(search_params)
    search_url = f"https://google.com/search?{encoded_params}"

    payload = {
        "method": "GET",
        "zone": "serp_api1",
        "url": search_url,
        "format": "json",
    }
    headers = {
        "Authorization": "Bearer 46536f1714a460eaf09bd68b4a344b88810168432875d300ebfed4e94fb51c76",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    result = response.json()
    body = json.loads(result["body"])
    assert body["organic"] is not None
    assert len(body["organic"]) >= 9
    assert body["organic"][0]["title"] is not None  
    assert body["organic"][0]["link"] is not None
    assert body["organic"][0]["description"] is not None
    pass


if __name__ == "__main__":
    test_bright_data_forward()