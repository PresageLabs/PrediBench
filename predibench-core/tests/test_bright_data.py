import os
import time
import urllib.parse
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


def _bright_data_creds_present() -> bool:
    return os.getenv("BRIGHT_DATA_BROWSER_ENDPOINT") is not None


@pytest.mark.skipif(
    not (_bright_data_creds_present() and os.getenv("SCRAPE_DO_API_KEY")),
    reason="Requires Bright Data Playwright credentials and SCRAPE_DO_API_KEY",
)
def test_compare_scrapers_on_search_results(tmp_path):
    """Use GoogleSearchTool to get URLs, then fetch each with Scrape.do and Bright Data.
    Saves each markdown to disk and prints timing comparison.
    """
    # Use Bright Data provider for Google search as in other tests
    search_tool = GoogleSearchTool(provider="bright_data", cutoff_date=None)
    search_md = search_tool.forward(SEARCH_QUERY)

    # Ensure we got some sources
    urls = [u for u in search_tool.sources if u.startswith("http")]
    assert len(urls) > 0

    # Limit to a reasonable number for test runtime
    urls = urls[:5]

    # Initialize tools once (persistent browser for Bright Data)
    scrape_do_tool = ScrapeDoVisitWebpageTool(render=True)
    bright_data_tool = BrightDataVisitWebpageTool()

    timings = []
    successes = 0

    for idx, url in enumerate(urls, start=1):
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.replace(":", "_").replace("/", "_")

        # Scrape.do
        t0 = time.perf_counter()
        try:
            md_sd = scrape_do_tool.forward(url)
            dt_sd = time.perf_counter() - t0
            assert isinstance(md_sd, str) and len(md_sd) > 0
            out_sd = tmp_path / f"search_{idx:02d}_scrape_do_{domain}.md"
            out_sd.write_text(md_sd, encoding="utf-8")
        except Exception as e:
            md_sd = f"ERROR: {e}"
            dt_sd = None

        # Bright Data Playwright
        t1 = time.perf_counter()
        try:
            md_bd = bright_data_tool.forward(url)
            dt_bd = time.perf_counter() - t1
            assert isinstance(md_bd, str) and len(md_bd) > 0
            out_bd = tmp_path / f"search_{idx:02d}_bright_data_{domain}.md"
            out_bd.write_text(md_bd, encoding="utf-8")
        except Exception as e:
            md_bd = f"ERROR: {e}"
            dt_bd = None

        timings.append({
            "url": url,
            "scrape_do_seconds": dt_sd,
            "bright_data_seconds": dt_bd,
            "scrape_do_ok": isinstance(md_sd, str) and not md_sd.startswith("ERROR:"),
            "bright_data_ok": isinstance(md_bd, str) and not md_bd.startswith("ERROR:"),
        })

        if isinstance(md_sd, str) and not md_sd.startswith("ERROR:") and isinstance(md_bd, str) and not md_bd.startswith("ERROR:"):
            successes += 1

    # Close Bright Data browser after loop
    try:
        bright_data_tool.close()
    except Exception:
        pass

    # At least one URL should succeed on both providers
    assert successes >= 1, f"No successful scrapes. Timings: {timings}"

    # Write timing summary
    summary_lines = [
        "url\tscrape_do_seconds\tbright_data_seconds\tscrape_do_ok\tbright_data_ok"
    ]
    for row in timings:
        summary_lines.append(
            f"{row['url']}\t{row['scrape_do_seconds']}\t{row['bright_data_seconds']}\t{row['scrape_do_ok']}\t{row['bright_data_ok']}"
        )
    (tmp_path / "timing_summary.tsv").write_text("\n".join(summary_lines), encoding="utf-8")
    print("\n".join(summary_lines))
