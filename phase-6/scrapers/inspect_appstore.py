"""
Inspect Apple App Store website structure to find correct CSS selectors
"""

import asyncio
from playwright.async_api import async_playwright

async def inspect_appstore():
    """Navigate to App Store and inspect the structure"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser
        page = await browser.new_page()
        
        # Navigate to Spotify App Store page
        url = "https://apps.apple.com/us/app/spotify-music-and-podcasts/id324684580"
        print(f"Navigating to: {url}")
        await page.goto(url, wait_until="networkidle", timeout=30000)
        
        # Wait for page to load
        await page.wait_for_timeout(3000)
        
        # Take screenshot
        await page.screenshot(path="appstore_page.png", full_page=True)
        print("Screenshot saved to appstore_page.png")
        
        # Try to find and click on reviews section
        try:
            # Look for various possible review section triggers
            review_buttons = [
                'text=Ratings & Reviews',
                'text=See All',
                'text=Reviews',
                '[data-test-bundle]',
                '.we-customer-review'
            ]
            
            for selector in review_buttons:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible():
                        print(f"Found element with selector: {selector}")
                        await element.click()
                        await page.wait_for_timeout(2000)
                        break
                except:
                    continue
        except Exception as e:
            print(f"Error clicking review section: {e}")
        
        # Get page HTML
        html_content = await page.content()
        
        # Save HTML for inspection
        with open("appstore_page.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("HTML saved to appstore_page.html")
        
        # Look for review-related elements
        print("\n=== Searching for review elements ===")
        
        # Try common review selectors
        selectors_to_try = [
            '.we-customer-review',
            '[data-test-bundle]',
            '.review',
            '.customer-review',
            '.rating',
            '.we-star-rating',
            '[class*="review"]',
            '[class*="rating"]'
        ]
        
        for selector in selectors_to_try:
            try:
                elements = await page.locator(selector).all()
                if elements:
                    print(f"Found {len(elements)} elements with selector: {selector}")
                    # Get first element's HTML
                    if elements:
                        first_html = await elements[0].inner_html()
                        print(f"First element HTML (truncated): {first_html[:200]}...")
            except:
                pass
        
        # Look for text content that might be reviews
        print("\n=== Looking for review text patterns ===")
        page_text = await page.inner_text("body")
        
        if "star" in page_text.lower():
            print("Found 'star' mentions in page")
        if "review" in page_text.lower():
            print("Found 'review' mentions in page")
        if "rating" in page_text.lower():
            print("Found 'rating' mentions in page")
        
        # Wait for user to inspect
        print("\nBrowser is open. Press Enter to close...")
        input()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_appstore())
