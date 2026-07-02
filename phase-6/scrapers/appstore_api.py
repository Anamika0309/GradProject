"""
Phase 6 – App Store Scraper (Apple RSS Feed – Real Reviews)
============================================================
Fetches REAL Spotify App Store reviews using Apple's public RSS feed API.
No API key required. No third-party library needed (pure stdlib + requests).

Apple RSS feed: https://itunes.apple.com/{country}/rss/customerreviews/
                page={page}/id={app_id}/sortby=mostrecent/json

Spotify App ID: 324684580
Free quota: unlimited (public RSS feed)
Target: 400+ reviews across US, GB, AU, CA, IN
"""

import json
import time
import hashlib
import logging
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

import urllib.request
import urllib.error

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Path setup ─────────────────────────────────────────────────────────────────
PHASE6_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PHASE6_DIR))

from dotenv import load_dotenv
load_dotenv(PHASE6_DIR / "config" / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [appstore] %(message)s")
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────
SPOTIFY_APP_ID = "324684580"
OUTPUT_DIR = PHASE6_DIR / "storage" / "raw"

# Countries to scrape (ISO codes)
TARGET_COUNTRIES = ["us", "gb", "au", "ca", "in", "ie", "nz", "za"]

# Apple RSS gives max 10 reviews per page, up to page 10 (100 per country)
MAX_PAGES_PER_COUNTRY = int(os.getenv("APP_STORE_MAX_PER_COUNTRY", "400")) // 10 or 10
MAX_PAGES_PER_COUNTRY = min(MAX_PAGES_PER_COUNTRY, 10)  # Apple caps at page 10

MIN_WORD_COUNT = 10
SLEEP_BETWEEN_REQUESTS = 1.0


def generate_id(country: str, review_id: str) -> str:
    raw = f"app_store_{country}_{review_id}"
    return "as_" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def fetch_page(country: str, page: int) -> list[dict]:
    """Fetch one page of reviews from Apple's RSS feed (returns up to 10 reviews)."""
    url = (
        f"https://itunes.apple.com/{country}/rss/customerreviews/"
        f"page={page}/id={SPOTIFY_APP_ID}/sortby=mostrecent/json"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; SpotifyReviewEngine/1.0)",
        "Accept": "application/json",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        feed = data.get("feed", {})
        entries = feed.get("entry", [])

        # First entry in page 1 is the app itself, not a review
        if page == 1 and entries and "im:rating" not in entries[0]:
            entries = entries[1:]

        return entries
    except urllib.error.HTTPError as e:
        if e.code == 400:
            # Apple returns 400 when page is beyond available reviews
            return []
        logger.warning(f"  HTTP {e.code} fetching {country} page {page}")
        return []
    except Exception as e:
        logger.warning(f"  Error fetching {country} page {page}: {e}")
        return []


def parse_entry(entry: dict, country: str) -> dict | None:
    """Parse an Apple RSS feed entry into the unified schema."""
    try:
        # Extract fields from Apple's nested JSON structure
        review_id = entry.get("id", {}).get("label", "")
        title = entry.get("title", {}).get("label", "")
        text = entry.get("content", {}).get("label", "").strip()
        author = entry.get("author", {}).get("name", {}).get("label", "anonymous")
        rating_str = entry.get("im:rating", {}).get("label", "")
        date_str = entry.get("updated", {}).get("label", "")
        vote_count = entry.get("im:voteCount", {}).get("label", "0")
        vote_sum = entry.get("im:voteSum", {}).get("label", "0")

        if not text:
            return None

        word_count = len(text.split())
        if word_count < MIN_WORD_COUNT:
            return None

        # Parse rating
        try:
            rating = int(rating_str)
        except (ValueError, TypeError):
            rating = None

        # Parse date
        try:
            iso_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).isoformat()
        except Exception:
            iso_date = datetime.now(timezone.utc).isoformat()

        return {
            "id": generate_id(country, review_id or text[:40]),
            "source": "app_store",
            "platform": f"ios_app_store_{country}",
            "text": text,
            "title": title or None,
            "author": author,
            "date": iso_date,
            "rating": rating,
            "language": "en",
            "url": f"https://apps.apple.com/{country}/app/spotify/{SPOTIFY_APP_ID}",
            "word_count": word_count,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "country": country,
                "score": None,
                "num_comments": None,
                "subreddit": None,
                "video_id": None,
                "video_title": None,
                "like_count": int(vote_count) if vote_count.isdigit() else 0,
                "flair": None,
            },
        }
    except Exception as e:
        logger.debug(f"  Parse error: {e}")
        return None


def scrape_country(country: str) -> list[dict]:
    """Scrape all available review pages for a given country."""
    records = []
    seen_ids: set[str] = set()

    for page in range(1, MAX_PAGES_PER_COUNTRY + 1):
        entries = fetch_page(country, page)

        if not entries:
            logger.info(f"  [{country.upper()}] Page {page}: no more reviews")
            break

        page_records = 0
        for entry in entries:
            parsed = parse_entry(entry, country)
            if parsed and parsed["id"] not in seen_ids:
                seen_ids.add(parsed["id"])
                records.append(parsed)
                page_records += 1

        logger.info(f"  [{country.upper()}] Page {page}: {page_records} reviews (total: {len(records)})")
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    return records


def run() -> list[dict]:
    """Scrape App Store reviews for Spotify across multiple countries."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"Scraping App Store reviews for Spotify (ID: {SPOTIFY_APP_ID})")
    logger.info(f"Countries: {', '.join(c.upper() for c in TARGET_COUNTRIES)}")
    logger.info(f"Max pages per country: {MAX_PAGES_PER_COUNTRY} (~{MAX_PAGES_PER_COUNTRY * 10} reviews each)")

    all_records: list[dict] = []
    seen_global: set[str] = set()

    for country in TARGET_COUNTRIES:
        logger.info(f"\nScraping {country.upper()}...")
        country_records = scrape_country(country)

        # Global dedup by review text fingerprint (same review sometimes appears in multiple countries)
        for rec in country_records:
            fp = rec["text"][:100]
            if fp not in seen_global:
                seen_global.add(fp)
                all_records.append(rec)

        logger.info(f"  [{country.upper()}] Added {len(country_records)} (global unique so far: {len(all_records)})")

    logger.info(f"\nApp Store total: {len(all_records)} reviews")

    out_path = OUTPUT_DIR / "app_store_reviews.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved -> {out_path}")

    return all_records


if __name__ == "__main__":
    results = run()
    print(f"\n[OK] App Store scrape complete: {len(results)} real reviews saved.")
