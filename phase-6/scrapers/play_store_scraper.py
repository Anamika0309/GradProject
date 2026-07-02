"""
Phase 6 – Google Play Store Scraper
=====================================
Scrapes Spotify reviews from the Google Play Store.
Uses `google-play-scraper` with continuation_token pagination for high volume.

Spotify Package: com.spotify.music
Target: ~3,000 reviews (1,000 per sort type × 3 sort types)
"""

import json
import time
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from google_play_scraper import Sort, reviews as gp_reviews
from tqdm import tqdm

# ── Configuration ──────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [play_store] %(message)s")
logger = logging.getLogger(__name__)

SPOTIFY_PACKAGE = "com.spotify.music"
MIN_WORD_COUNT = 10
BATCH_SIZE = 200          # Reviews per API call (max allowed)
MAX_PER_SORT = 1000       # Reviews per sort type
SLEEP_BETWEEN_BATCHES = 1.5  # Seconds (avoid rate limiting)
OUTPUT_DIR = Path(__file__).parent.parent / "storage" / "raw"

SORT_TYPES = [
    (Sort.MOST_RELEVANT, "Most Relevant"),
    (Sort.NEWEST, "Newest"),
    (Sort.RATING, "By Rating"),
]


def generate_id(review_id: str) -> str:
    raw = f"play_store_{review_id}"
    return "ps_" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def fetch_with_pagination(sort_type, sort_label: str, max_reviews: int) -> list[dict]:
    """Fetch reviews using continuation_token loop for maximum volume."""
    collected = []
    token = None
    fetched = 0

    pbar = tqdm(total=max_reviews, desc=f"Play Store [{sort_label}]", unit="reviews")

    while fetched < max_reviews:
        count = min(BATCH_SIZE, max_reviews - fetched)
        try:
            batch, token = gp_reviews(
                SPOTIFY_PACKAGE,
                lang="en",
                country="us",
                sort=sort_type,
                count=count,
                continuation_token=token,
            )
        except Exception as exc:
            logger.warning(f"  Batch error ({sort_label}): {exc}")
            time.sleep(5)
            break

        if not batch:
            break

        collected.extend(batch)
        fetched += len(batch)
        pbar.update(len(batch))
        time.sleep(SLEEP_BETWEEN_BATCHES)

        if token is None:
            break  # No more pages

    pbar.close()
    return collected


def normalize_review(raw: dict) -> dict | None:
    """Map Play Store raw review → unified schema."""
    text = (raw.get("content") or "").strip()
    word_count = len(text.split())
    if word_count < MIN_WORD_COUNT:
        return None

    date_val = raw.get("at")
    if isinstance(date_val, datetime):
        iso_date = date_val.astimezone(timezone.utc).isoformat()
    else:
        iso_date = datetime.now(timezone.utc).isoformat()

    review_id = str(raw.get("reviewId") or hash(text))

    return {
        "id": generate_id(review_id),
        "source": "play_store",
        "platform": "google_play",
        "text": text,
        "title": None,  # Play Store reviews don't have titles
        "author": raw.get("userName") or "anonymous",
        "date": iso_date,
        "rating": int(raw.get("score", 0)) or None,
        "language": "en",
        "url": f"https://play.google.com/store/apps/details?id={SPOTIFY_PACKAGE}",
        "word_count": word_count,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "country": "us",
            "score": raw.get("thumbsUpCount"),
            "num_comments": None,
            "subreddit": None,
            "video_id": None,
            "video_title": None,
            "like_count": raw.get("thumbsUpCount"),
            "flair": None,
        },
    }


def run() -> list[dict]:
    """Run the full Play Store scrape across all sort types."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_reviews: list[dict] = []
    seen_ids: set[str] = set()

    for sort_type, sort_label in SORT_TYPES:
        raw_batch = fetch_with_pagination(sort_type, sort_label, MAX_PER_SORT)
        logger.info(f"  Raw from '{sort_label}': {len(raw_batch)} reviews")

        for raw in raw_batch:
            review_id = str(raw.get("reviewId") or "")
            if review_id in seen_ids:
                continue
            normalized = normalize_review(raw)
            if normalized is None:
                continue
            seen_ids.add(review_id)
            all_reviews.append(normalized)

        time.sleep(3)  # Pause between sort type switches

    logger.info(f"Play Store total after filtering & dedup: {len(all_reviews)} reviews")

    out_path = OUTPUT_DIR / "play_store_reviews.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_reviews, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved → {out_path}")

    return all_reviews


if __name__ == "__main__":
    results = run()
    print(f"\n✅  Play Store scrape complete: {len(results)} reviews saved.")
