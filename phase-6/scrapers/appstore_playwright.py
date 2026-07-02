"""
Phase 6 – App Store Scraper (Playwright-based)
================================================
Scrapes Spotify reviews from the Apple App Store using Playwright.
This avoids the dependency conflicts with the app-store-scraper package.

Spotify iOS App ID: 324684580
Target: ~400 reviews × 5 countries = ~2,000 reviews
"""

import json
import time
import hashlib
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict

from playwright.async_api import async_playwright, Page
from tqdm import tqdm

# ── Configuration ──────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [appstore] %(message)s")
logger = logging.getLogger(__name__)

SPOTIFY_APP_ID = "324684580"
SPOTIFY_APP_NAME = "spotify-music-and-podcasts"

# Countries to scrape (ISO country codes)
COUNTRIES = [
    {"code": "us", "label": "United States", "url": "https://apps.apple.com/us/app/spotify-music-and-podcasts/id324684580"},
    {"code": "gb", "label": "United Kingdom", "url": "https://apps.apple.com/gb/app/spotify-music-and-podcasts/id324684580"},
    {"code": "au", "label": "Australia", "url": "https://apps.apple.com/au/app/spotify-music-and-podcasts/id324684580"},
    {"code": "ca", "label": "Canada", "url": "https://apps.apple.com/ca/app/spotify-music-and-podcasts/id324684580"},
    {"code": "in", "label": "India", "url": "https://apps.apple.com/in/app/spotify-music-and-podcasts/id324684580"},
]

MAX_PER_COUNTRY = 400
MIN_WORD_COUNT = 10
OUTPUT_DIR = Path(__file__).parent.parent / "storage" / "raw"


def generate_id(source: str, country: str, review_id: str) -> str:
    """Deterministic unique ID for each review."""
    raw = f"{source}_{country}_{review_id}"
    return "as_" + hashlib.sha256(raw.encode()).hexdigest()[:16]


async def scrape_country_reviews(page: Page, country_code: str, country_label: str, url: str) -> List[Dict]:
    """Scrape reviews for one country store using Playwright."""
    logger.info(f"Scraping App Store [{country_label}] (up to {MAX_PER_COUNTRY} reviews)…")
    
    reviews = []
    try:
        # Navigate to the app page
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        
        # Click on "See All" reviews button if it exists
        try:
            see_all_button = page.locator('a[href*="reviews"]').first
            if await see_all_button.is_visible():
                await see_all_button.click()
                await page.wait_for_timeout(2000)
        except:
            logger.info(f"No 'See All' button found for {country_label}, trying alternative...")
        
        # Try to find and click on reviews section
        try:
            # Look for reviews tab or section
            reviews_tab = page.locator('text=Reviews').first
            if await reviews_tab.is_visible():
                await reviews_tab.click()
                await page.wait_for_timeout(2000)
        except:
            pass
        
        # Scroll to load reviews
        scroll_count = 0
        max_scrolls = 20  # Limit scrolls to avoid infinite loops
        
        while len(reviews) < MAX_PER_COUNTRY and scroll_count < max_scrolls:
            # Try to extract reviews from current page
            try:
                # Look for review elements - App Store uses various selectors
                review_elements = await page.locator('[data-test-rating], .we-customer-review, .review').all()
                
                for element in review_elements:
                    if len(reviews) >= MAX_PER_COUNTRY:
                        break
                    
                    try:
                        # Extract review data
                        text = await element.inner_text()
                        if text and len(text.strip()) > 20:
                            # Try to extract rating
                            rating = None
                            try:
                                rating_element = element.locator('[aria-label*="stars"], .we-star-rating').first
                                if await rating_element.is_visible():
                                    aria_label = await rating_element.get_attribute('aria-label')
                                    if aria_label:
                                        # Extract number from "5 stars" etc
                                        pass
                            except:
                                pass
                            
                            # Extract author if possible
                            author = "anonymous"
                            try:
                                author_element = element.locator('.we-customer-review__user, .author').first
                                if await author_element.is_visible():
                                    author = await author_element.inner_text()
                            except:
                                pass
                            
                            reviews.append({
                                "text": text.strip(),
                                "rating": rating,
                                "author": author,
                                "date": datetime.now(timezone.utc).isoformat()
                            })
                    except Exception as e:
                        continue
                
            except Exception as e:
                logger.warning(f"Error extracting reviews: {e}")
            
            # Scroll down to load more
            await page.evaluate("window.scrollBy(0, 800)")
            await page.wait_for_timeout(1500)
            scroll_count += 1
            
            logger.info(f"  Collected {len(reviews)} reviews so far (scroll {scroll_count}/{max_scrolls})")
        
        logger.info(f"  Total collected from {country_label}: {len(reviews)} reviews")
        
    except Exception as exc:
        logger.warning(f"  Failed for {country_label}: {exc}")
    
    return reviews


def normalize_review(raw: Dict, country_code: str) -> Dict | None:
    """Map raw review → unified schema."""
    text = (raw.get("text") or "").strip()
    word_count = len(text.split())
    if word_count < MIN_WORD_COUNT:
        return None

    review_id = str(hash(text))

    return {
        "id": generate_id("app_store", country_code, review_id),
        "source": "app_store",
        "platform": f"ios_app_store_{country_code}",
        "text": text,
        "title": None,
        "author": raw.get("author") or "anonymous",
        "date": raw.get("date") or datetime.now(timezone.utc).isoformat(),
        "rating": raw.get("rating"),
        "language": "en",
        "url": f"https://apps.apple.com/{country_code}/app/spotify/{SPOTIFY_APP_ID}",
        "word_count": word_count,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "country": country_code,
            "score": None,
            "num_comments": None,
            "subreddit": None,
            "video_id": None,
            "video_title": None,
            "like_count": None,
            "flair": None,
        },
    }


async def run_async():
    """Run the full App Store scrape across all countries."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_reviews = []
    seen_texts = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        for country in tqdm(COUNTRIES, desc="Countries"):
            raw_reviews = await scrape_country_reviews(page, country["code"], country["label"], country["url"])
            
            for raw in raw_reviews:
                normalized = normalize_review(raw, country["code"])
                if normalized is None:
                    continue
                # De-dupe
                fingerprint = normalized["text"][:120]
                if fingerprint in seen_texts:
                    continue
                seen_texts.add(fingerprint)
                all_reviews.append(normalized)
            
            time.sleep(2)  # Be polite between country requests
        
        await browser.close()

    logger.info(f"App Store total after filtering: {len(all_reviews)} reviews")

    out_path = OUTPUT_DIR / "app_store_reviews.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_reviews, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved → {out_path}")

    return all_reviews


def run():
    """Synchronous wrapper for async function."""
    return asyncio.run(run_async())


if __name__ == "__main__":
    results = run()
    print(f"\n✅  App Store scrape complete: {len(results)} reviews saved.")
