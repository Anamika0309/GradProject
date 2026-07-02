"""
Phase 6 – Data Normalizer
==========================
Validates and enforces the unified review schema across all raw scraper outputs.

Rules applied:
  - Keep reviews with > 5 words
  - Strip all emojis and special Unicode symbols
  - Drop non-English reviews (langdetect)
  - Enforce required schema fields
"""

import json
import re
import hashlib
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from langdetect import detect, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [normalizer] %(message)s")
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────
MIN_WORD_COUNT = 5                  # User requirement: keep reviews > 5 words
REQUIRED_FIELDS = {"id", "source", "platform", "text", "date", "word_count"}
VALID_SOURCES = {"app_store", "play_store", "reddit", "community_forum", "social_media"}

# Unicode ranges that cover emojis and pictographic symbols
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"   # emoticons
    "\U0001F300-\U0001F5FF"   # symbols & pictographs
    "\U0001F680-\U0001F6FF"   # transport & map
    "\U0001F700-\U0001F77F"   # alchemical symbols
    "\U0001F780-\U0001F7FF"   # geometric shapes extended
    "\U0001F800-\U0001F8FF"   # supplemental arrows-c
    "\U0001F900-\U0001F9FF"   # supplemental symbols & pictographs
    "\U0001FA00-\U0001FA6F"   # chess symbols
    "\U0001FA70-\U0001FAFF"   # symbols & pictographs extended-a
    "\U00002702-\U000027B0"   # dingbats
    "\U000024C2-\U0001F251"   # enclosed characters
    "\U0001F004"              # mahjong tile
    "\U0001F0CF"              # playing card black joker
    "\U0000200D"              # zero-width joiner
    "\U0000FE0F"              # variation selector-16
    "\U00002640-\U00002642"   # gender signs
    "\U00002600-\U00002B55"   # misc symbols
    "\U0000231A-\U0000231B"   # watch, hourglass
    "\U000023E9-\U000023F3"   # fast-forward etc.
    "\U000023F8-\U000023FA"   # pause, stop, record
    "]+",
    flags=re.UNICODE,
)


def remove_emojis(text: str) -> str:
    """Strip all emoji and pictographic characters from text."""
    cleaned = _EMOJI_PATTERN.sub("", text)
    # Also remove leftover whitespace from emoji removal
    cleaned = re.sub(r" {2,}", " ", cleaned).strip()
    return cleaned


def detect_language(text: str) -> str:
    """Detect text language. Returns 'en' on failure (safe default)."""
    if not LANGDETECT_AVAILABLE:
        return "en"
    try:
        return detect(text[:500])
    except LangDetectException:
        return "unknown"


def ensure_id(record: dict) -> str:
    """Generate a stable ID if missing."""
    raw = f"{record.get('source','x')}_{record.get('url','x')}_{record.get('text','x')[:80]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:18]


def normalize(record: dict, enforce_english: bool = True) -> dict | None:
    """
    Validate and clean a single record.
    Returns None if the record should be discarded.

    Steps:
      1. Check required fields
      2. Remove emojis from text
      3. Drop if < 5 words after cleaning
      4. Drop if non-English (when enforce_english=True)
    """
    # 1. Ensure all required fields exist
    for field in REQUIRED_FIELDS:
        if field not in record:
            return None

    # 2. Validate source
    if record.get("source") not in VALID_SOURCES:
        return None

    # 3. Clean text — strip emojis first
    text = (record.get("text") or "").strip()
    if not text:
        return None

    text = remove_emojis(text)
    if not text:
        return None

    # 4. Word count check (> 5 words)
    word_count = len(text.split())
    if word_count <= MIN_WORD_COUNT:
        return None

    # 5. Language check — drop non-English
    lang = record.get("language") or detect_language(text)
    if enforce_english and lang not in ("en", "unknown"):
        return None

    # Ensure ID
    record_id = record.get("id") or ensure_id(record)

    # Normalize date
    date_val = record.get("date")
    if not date_val:
        date_val = datetime.now(timezone.utc).isoformat()

    # Build clean record with guaranteed schema shape
    clean = {
        "id": record_id,
        "source": record["source"],
        "platform": record.get("platform") or record["source"],
        "text": text,
        "title": (record.get("title") or None),
        "author": record.get("author") or "anonymous",
        "date": date_val,
        "rating": record.get("rating"),
        "language": lang,
        "url": record.get("url"),
        "word_count": word_count,
        "scraped_at": record.get("scraped_at") or datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "score":        record.get("metadata", {}).get("score"),
            "num_comments": record.get("metadata", {}).get("num_comments"),
            "subreddit":    record.get("metadata", {}).get("subreddit"),
            "country":      record.get("metadata", {}).get("country"),
            "video_id":     record.get("metadata", {}).get("video_id"),
            "video_title":  record.get("metadata", {}).get("video_title"),
            "like_count":   record.get("metadata", {}).get("like_count"),
            "flair":        record.get("metadata", {}).get("flair"),
        },
    }
    return clean


def normalize_file(raw_path: Path, enforce_english: bool = True) -> list[dict]:
    """Normalize all records in a raw JSON file."""
    if not raw_path.exists():
        logger.warning(f"File not found: {raw_path}")
        return []

    with open(raw_path, encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list):
        logger.warning(f"Expected a list in {raw_path}, got {type(records)}")
        return []

    cleaned = []
    skipped = 0
    for record in records:
        result = normalize(record, enforce_english)
        if result:
            cleaned.append(result)
        else:
            skipped += 1

    logger.info(f"  {raw_path.name}: {len(cleaned)} kept, {skipped} discarded")
    return cleaned


def normalize_all(raw_dir: Path, enforce_english: bool = True) -> list[dict]:
    """Normalize all raw scraper output files."""
    all_records: list[dict] = []
    raw_files = [
        raw_dir / "app_store_reviews.json",
        raw_dir / "play_store_reviews.json",
        raw_dir / "reddit_reviews.json",
        raw_dir / "forum_reviews.json",
        raw_dir / "social_media_reviews.json",
    ]

    for raw_file in raw_files:
        records = normalize_file(raw_file, enforce_english)
        all_records.extend(records)

    logger.info(f"Normalization complete: {len(all_records)} total records")
    return all_records
