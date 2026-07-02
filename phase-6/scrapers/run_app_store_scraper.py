"""
Runner for App Store scraping that avoids import shadowing with the local module name.
Saves output to phase-6/storage/raw/app_store_reviews.json
"""

import json
import time
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
import sys
import os

# Ensure we import the installed `app_store_scraper` package, not the local file
scrapers_dir = str(Path(__file__).parent.resolve())
if scrapers_dir in sys.path:
    sys.path.remove(scrapers_dir)

from app_store_scraper import AppStore

from app_store_scraper import AppStore
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s [app_store_runner] %(message)s")
logger = logging.getLogger(__name__)

SPOTIFY_APP_ID = "324684580"
SPOTIFY_APP_NAME = "spotify-music-and-podcasts"

COUNTRIES = [
    {"code": "us", "label": "United States"},
    {"code": "gb", "label": "United Kingdom"},
    {"code": "au", "label": "Australia"},
    {"code": "ca", "label": "Canada"},
    {"code": "in", "label": "India"},
]

MAX_PER_COUNTRY = 400
MIN_WORD_COUNT = 10
OUTPUT_DIR = Path(__file__).parent.parent / "storage" / "raw"


def generate_id(source: str, country: str, review_id: str) -> str:
    raw = f"{source}_{country}_{review_id}"
    return "as_" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def scrape_country(country_code: str, country_label: str) -> list[dict]:
    logger.info(f"Scraping App Store [{country_label}] (up to {MAX_PER_COUNTRY} reviews)…")
    try:
        app = AppStore(
            country=country_code,
            app_name=SPOTIFY_APP_NAME,
            app_id=SPOTIFY_APP_ID,
        )
        app.review(how_many=MAX_PER_COUNTRY, sleep=0.5)
        return app.reviews or []
    except Exception as exc:
        logger.warning(f"  Failed for {country_label}: {exc}")
        return []


def normalize_review(raw: dict, country_code: str) -> dict | None:
    text = (raw.get("review") or "").strip()
    word_count = len(text.split())
    if word_count < MIN_WORD_COUNT:
        return None

    date_val = raw.get("date")
    if isinstance(date_val, datetime):
        iso_date = date_val.astimezone(timezone.utc).isoformat()
    else:
        iso_date = datetime.now(timezone.utc).isoformat()

    review_id = str(raw.get("reviewId") or raw.get("id") or hash(text))

    return {
        "id": generate_id("app_store", country_code, review_id),
        "source": "app_store",
        "platform": f"ios_app_store_{country_code}",
        "text": text,
        "title": (raw.get("title") or "").strip() or None,
        "author": raw.get("userName") or "anonymous",
        "date": iso_date,
        "rating": int(raw.get("rating", 0)) or None,
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


def run() -> list[dict]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_reviews: list[dict] = []
    seen_texts: set[str] = set()

    for country in tqdm(COUNTRIES, desc="Countries"):
        raw_reviews = scrape_country(country["code"], country["label"])
        logger.info(f"  Raw: {len(raw_reviews)} reviews from {country['label']}")

        for raw in raw_reviews:
            normalized = normalize_review(raw, country["code"])
            if normalized is None:
                continue
            fingerprint = normalized["text"][:120]
            if fingerprint in seen_texts:
                continue
            seen_texts.add(fingerprint)
            all_reviews.append(normalized)

        time.sleep(2)

    logger.info(f"App Store total after filtering: {len(all_reviews)} reviews")

    out_path = OUTPUT_DIR / "app_store_reviews.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_reviews, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved → {out_path}")

    return all_reviews


if __name__ == "__main__":
    results = run()
    print(f"\n✅  App Store scrape complete: {len(results)} reviews saved.")
