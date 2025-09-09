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
    
def not_great_test_bright_data_sdk():
    from brightdata import bdclient

    client = bdclient(api_token=os.getenv("BRIGHT_SERPER_API_KEY")) # Can also be taken from .env file

    results = client.scrape(query="september 2025 federal reserve meeting expectations september 2025 rate cut probability", response_format="json")
    # Try adding parameters like: search_engine="bing"/"yandex", country="gb"

    results = client.parse_content(results)
    pass 
    # Try parsing the result for easy to read result / low token usage
    
def test_bright_data_playwright():
    import asyncio
    from os import environ
    from playwright.async_api import Playwright, async_playwright
    from markdownify import markdownify as md

    # Replace with your Browser API zone credentials
    AUTH = environ.get('AUTH', default='USER:PASS')
    TARGET_URL = environ.get('TARGET_URL', default='https://www.cnbc.com/2025/09/08/traders-see-a-chance-the-fed-cuts-by-a-half-point.html')

    async def scrape(playwright: Playwright, url=TARGET_URL):
        if AUTH == 'USER:PASS':
            raise Exception('Provide Browser API credentials in AUTH '
                            'environment variable or update the script.')
        print('Connecting to Browser...')
        endpoint_url = f'wss://{AUTH}@brd.superproxy.io:9222'
        browser = await playwright.chromium.connect_over_cdp(endpoint_url)
        try:
            print(f'Connected! Navigating to {url}...')
            page = await browser.new_page()
            client = await page.context.new_cdp_session(page)
            frames = await client.send('Page.getFrameTree')
            frame_id = frames['frameTree']['frame']['id']
            inspect = await client.send('Page.inspect', {
                'frameId': frame_id,
            })
            inspect_url = inspect['url']
            print(f'You can inspect this session at: {inspect_url}.')
            await page.goto(url, timeout=2*60_000)
            print('Navigated! Scraping page content...')
            data = await page.content()
            print(f'Scraped! Data: {data}')
            markdown_content = md(data, heading_style="ATX")
            
            # Save HTML content to file
            with open('scraped_content.html', 'w', encoding='utf-8') as f:
                f.write(data)
            print('HTML content saved to scraped_content.html')
            
            # Save markdown content to file
            with open('scraped_content.md', 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print('Markdown content saved to scraped_content.md')
            
            return markdown_content, data
        finally:
            await browser.close()

    async def main():
        async with async_playwright() as playwright:
            return await scrape(playwright)

    return asyncio.run(main())



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
        "Authorization": "Bearer "+os.getenv("BRIGHT_SERPER_API_KEY"),
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
    test_bright_data_playwright()