import os
import time
import urllib.parse
from pathlib import Path
import pytest
from predibench.agent.smolagents_utils import (
    GoogleSearchTool,
    VisitWebpageTool,
    BrightDataVisitWebpageTool,
    ScrapeDoVisitWebpageTool,
)

SEARCH_QUERY = "september 2025 federal reserve meeting expectations september 2025 rate cut probability"
TARGET_URL = "https://www.cnbc.com/2025/09/08/traders-see-a-chance-the-fed-cuts-by-a-half-point.html"


def test_bright_data_forward():
    """Test Bright Data provider forward method."""
    
    # Create tool and test
    tool = GoogleSearchTool(provider="bright_data", cutoff_date=None)
    result = tool.forward(SEARCH_QUERY)
    
    # Basic assertions
    assert isinstance(result, str)
    assert len(result) > 0
    assert "Search Results for" in result
    assert "september 2025 federal reserve" in result.lower()
    print(f"Result: {result}")
    
def not_great_test_bright_data_sdk():
    from brightdata import bdclient

    client = bdclient(api_token=os.getenv("BRIGHT_SERPER_API_KEY")) # Can also be taken from .env file

    results = client.scrape(query=SEARCH_QUERY, response_format="json")
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
        endpoint_url = f'wss://brd-customer-hl_db87adc5-zone-scraping_browser1:4ylnjp14fyzm@brd.superproxy.io:9222'
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
        
    # test TextAgent

    return asyncio.run(main())

def test_visit_webpage_tool():
    tool = VisitWebpageTool()
    result = tool.forward(TARGET_URL)
    assert isinstance(result, str)
    assert len(result) > 0
    assert "CNBC" in result
    print(f"Result: {result}")

def test_scrape_do():
    import requests
    import urllib.parse

    # URL encode the target URL for proper API usage
    encoded_target_url = urllib.parse.quote(TARGET_URL)
    
    # Build the scrape.do API URL with proper parameter substitution
    scrape_api_url = f"http://api.scrape.do/?url={encoded_target_url}&token={os.getenv('SCRAPE_DO_API_KEY')}&output=markdown&render=true"
    
    # Make the API request
    response = requests.get(scrape_api_url)
    
    # Print and validate response
    print(response.text)
    with open('scraped_content_scrape_do.md', 'w', encoding='utf-8') as f:
        f.write(response.text)
    print('Markdown content saved to scraped_content.md')
    
    # Basic assertions to ensure the request worked
    assert response.status_code == 200
    assert len(response.text) > 0

def test_bright_data():
    import requests
    import json
    from urllib.parse import urlencode
    url = "https://api.brightdata.com/request"

    # Define search parameters as dictionary
    search_params = {
        "q": SEARCH_QUERY,  # Example with spaces
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
    test_scrape_do()

tmp_path = Path(".")
def test_compare_scrapers_on_search_results(tmp_path=tmp_path):
    """Compare Scrape.do and Bright Data on top Google results.

    Simpler flow: get a few URLs, fetch each with both providers,
    save markdown files, and print basic durations using time.time().
    """
    # Search via Bright Data-backed Google tool
    search_tool = GoogleSearchTool(provider="bright_data", cutoff_date=None)
    _ = search_tool.forward(SEARCH_QUERY)

    # Collect a few valid URLs
    urls = [u for u in search_tool.sources if isinstance(u, str) and u.startswith("http")]
    assert len(urls) > 0
    urls = urls[:5]

    # Initialize both scrapers
    scrape_do_tool = ScrapeDoVisitWebpageTool(render=True)
    bright_data_tool = BrightDataVisitWebpageTool()

    successes = 0

    for idx, url in enumerate(urls, start=1):
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.replace(":", "_").replace("/", "_")

        print(f"\n[{idx}] URL: {url}")

        # Scrape.do
        try:
            t0 = time.time()
            md_sd = scrape_do_tool.forward(url)
            dt_sd = time.time() - t0
            assert isinstance(md_sd, str) and len(md_sd) > 0
            (tmp_path / f"search_{idx:02d}_scrape_do_{domain}.md").write_text(md_sd, encoding="utf-8")
            print(f"Scrape.do: OK in ~{dt_sd:.2f}s")
        except Exception as e:
            md_sd = None
            print(f"Scrape.do: ERROR {e}")

        # Bright Data
        try:
            t1 = time.time()
            md_bd = bright_data_tool.forward(url)
            dt_bd = time.time() - t1
            assert isinstance(md_bd, str) and len(md_bd) > 0
            (tmp_path / f"search_{idx:02d}_bright_data_{domain}.md").write_text(md_bd, encoding="utf-8")
            print(f"Bright Data: OK in ~{dt_bd:.2f}s")
        except Exception as e:
            md_bd = None
            print(f"Bright Data: ERROR {e}")

        if md_sd and md_bd:
            successes += 1

    # Try to close any persistent Bright Data browser
    try:
        bright_data_tool.close()
    except Exception:
        pass

    # Ensure at least one pair worked
    assert successes >= 1, "No successful scrapes from both providers"

if __name__ == "__main__":
    test_compare_scrapers_on_search_results()
