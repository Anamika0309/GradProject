"""
Phase 6 – Scraping Orchestrator
=================================
CLI tool that runs all scrapers, normalises the output, deduplicates,
and produces a single `storage/processed/all_reviews.json` dataset.

Usage:
  python orchestrator.py                      # Run all sources
  python orchestrator.py --sources reddit     # Run only Reddit
  python orchestrator.py --sources app_store play_store
  python orchestrator.py --dry-run            # Check connectivity only
  python orchestrator.py --no-near-dedup      # Skip slow near-dedup
  python orchestrator.py --stats              # Show stats on existing data

Output:
  storage/raw/<source>_reviews.json     ← per-source raw output
  storage/processed/all_reviews.json    ← merged + deduplicated final dataset
  storage/processed/run_summary.json    ← stats for this run
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 output on Windows (prevents cp1252 UnicodeEncodeError)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ── Path setup ─────────────────────────────────────────────────────────────────
PHASE6_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PHASE6_DIR))

from pipeline.normalizer import normalize_all
from pipeline.deduplicator import run_deduplication

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [orchestrator] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(PHASE6_DIR / "storage" / "orchestrator.log", mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── Source Registry ────────────────────────────────────────────────────────────
# Lazy imports so missing credentials don't crash the whole CLI on startup
SOURCE_REGISTRY = {
    "app_store": {
        "module": "scrapers.appstore_api",
        "label": "App Store (iOS)",
        "requires_key": False,
    },
    "play_store": {
        "module": "scrapers.play_store_scraper",
        "label": "Google Play Store",
        "requires_key": False,
    },
    "reddit": {
        "module": "scrapers.reddit_scraper",
        "label": "Reddit",
        "requires_key": True,
        "key_env": "REDDIT_CLIENT_ID",
    },
    "community_forum": {
        "module": "scrapers.community_forum_scraper",
        "label": "Spotify Community Forum",
        "requires_key": False,
    },
    "social_media": {
        "module": "scrapers.social_media_scraper",
        "label": "YouTube (Social Media)",
        "requires_key": True,
        "key_env": "YOUTUBE_API_KEY",
    },
}

RAW_DIR = PHASE6_DIR / "storage" / "raw"
PROCESSED_DIR = PHASE6_DIR / "storage" / "processed"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _print_banner():
    print("\n" + "=" * 60)
    print("  Phase 6 - Spotify Review Scraping Orchestrator")
    print("  AI-Powered Review Discovery Engine")
    print("=" * 60 + "\n")


def _load_env():
    """Load .env if present."""
    from dotenv import load_dotenv
    env_path = PHASE6_DIR / "config" / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Loaded credentials from {env_path}")
    else:
        logger.warning(
            f"No .env found at {env_path}. "
            "Copy config/config.example.env → config/.env and fill in credentials."
        )


def _check_credentials(source_key: str) -> bool:
    """Check if required environment variables are set for a source."""
    import os
    info = SOURCE_REGISTRY.get(source_key, {})
    if not info.get("requires_key"):
        return True
    key_env = info.get("key_env", "")
    value = os.getenv(key_env, "")
    if not value or "your_" in value.lower():
        logger.warning(
            f"⚠️  {info['label']}: Missing credential {key_env}. "
            f"Add it to config/.env to enable this source."
        )
        return False
    return True


def _run_scraper(source_key: str) -> list[dict]:
    """Dynamically import and run a scraper module."""
    import importlib
    info = SOURCE_REGISTRY[source_key]
    label = info["label"]

    logger.info(f"\n{'- '*25}")
    logger.info(f"Starting: {label}")
    logger.info(f"{'- '*25}")

    t0 = time.time()
    try:
        mod = importlib.import_module(info["module"])
        results = mod.run()
        elapsed = round(time.time() - t0, 1)
        logger.info(f"✅  {label}: {len(results)} records in {elapsed}s")
        return results
    except Exception as exc:
        logger.error(f"❌  {label} failed: {exc}")
        return []


def _show_stats(processed_path: Path):
    """Print stats on an existing processed dataset."""
    if not processed_path.exists():
        print("No processed dataset found. Run the scraper first.")
        return

    with open(processed_path, encoding="utf-8") as f:
        data = json.load(f)

    total = len(data)
    by_source: dict[str, int] = {}
    by_rating: dict[str, int] = {}
    word_counts = []

    for r in data:
        src = r.get("source", "unknown")
        by_source[src] = by_source.get(src, 0) + 1
        rating = r.get("rating")
        key = str(rating) if rating else "none"
        by_rating[key] = by_rating.get(key, 0) + 1
        word_counts.append(r.get("word_count", 0))

    avg_words = round(sum(word_counts) / max(len(word_counts), 1))

    print(f"\n" + "=" * 50)
    print(f"  Dataset: {processed_path.name}")
    print(f"  Total reviews: {total:,}")
    print(f"  Average word count: {avg_words}")
    print(f"\n  By source:")
    for src, count in sorted(by_source.items(), key=lambda x: -x[1]):
        pct = round(count / total * 100)
        bar = "#" * (pct // 3)
        print(f"    {src:<22} {count:>5,}  ({pct:>3}%)  {bar}")
    print(f"\n  By rating:")
    for rating in sorted(by_rating.keys(), key=lambda x: (x == "none", x)):
        count = by_rating[rating]
        pct = round(count / total * 100)
        stars = (str(rating) + " stars") if rating != "none" else "N/A"
        print(f"    {stars:<10}  {count:>5,}  ({pct}%)")
    print("=" * 50 + "\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    _print_banner()

    parser = argparse.ArgumentParser(
        description="Phase 6 Scraping Orchestrator – Spotify Review Discovery Engine"
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=list(SOURCE_REGISTRY.keys()) + ["all"],
        default=["all"],
        help="Which sources to scrape (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check connectivity and credentials without scraping",
    )
    parser.add_argument(
        "--no-near-dedup",
        action="store_true",
        help="Skip slow near-duplicate detection (faster for large datasets)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics on the existing processed dataset and exit",
    )
    args = parser.parse_args()

    # Show stats mode
    if args.stats:
        _show_stats(PROCESSED_DIR / "all_reviews.json")
        return

    _load_env()

    # Resolve source list
    sources = list(SOURCE_REGISTRY.keys()) if "all" in args.sources else args.sources

    # Dry-run: just check credentials
    if args.dry_run:
        print("Dry-run mode - checking credentials and connectivity:\n")
        for src in sources:
            label = SOURCE_REGISTRY[src]["label"]
            ok = _check_credentials(src)
            status = "[OK]  Ready" if ok else "[!!] Missing credentials"
            print(f"  {label:<35} {status}")
        print("\nRun without --dry-run to start scraping.")
        return

    # Create output directories
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    run_start = datetime.now(timezone.utc)
    logger.info(f"Run started at: {run_start.isoformat()}")
    logger.info(f"Sources: {', '.join(sources)}")

    # ── Step 1: Scrape ─────────────────────────────────────────────────────────
    source_stats: dict[str, int] = {}
    for source_key in sources:
        if not _check_credentials(source_key):
            logger.warning(f"Skipping {source_key} — credentials not configured.")
            source_stats[source_key] = 0
            continue
        results = _run_scraper(source_key)
        source_stats[source_key] = len(results)

    # ── Step 2: Normalize ──────────────────────────────────────────────────────
    logger.info("\n" + "─" * 50)
    logger.info("Normalizing all raw outputs…")
    normalized = normalize_all(RAW_DIR, enforce_english=True)
    logger.info(f"Normalized: {len(normalized)} records")

    # ── Step 3: Deduplicate ────────────────────────────────────────────────────
    logger.info("Deduplicating…")
    near_dedup = not args.no_near_dedup
    final_records, dedup_stats = run_deduplication(normalized, near_dedup=near_dedup)

    # ── Step 4: Save ───────────────────────────────────────────────────────────
    out_path = PROCESSED_DIR / "all_reviews.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(final_records, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved final dataset → {out_path}")

    # ── Step 5: Summary ────────────────────────────────────────────────────────
    run_end = datetime.now(timezone.utc)
    run_duration = round((run_end - run_start).total_seconds() / 60, 1)

    summary = {
        "run_start": run_start.isoformat(),
        "run_end": run_end.isoformat(),
        "duration_minutes": run_duration,
        "sources_scraped": sources,
        "raw_by_source": source_stats,
        "normalized_total": len(normalized),
        "deduplication": dedup_stats,
        "final_review_count": len(final_records),
        "output_file": str(out_path),
    }

    summary_path = PROCESSED_DIR / "run_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Print final report
    print("\n" + "=" * 60)
    print("  Phase 6 Scraping Complete!")
    print("=" * 60)
    print(f"\n  Duration:          {run_duration} minutes")
    print(f"\n  Reviews by source:")
    for src, count in source_stats.items():
        print(f"    {SOURCE_REGISTRY[src]['label']:<35} {count:>6,}")
    print(f"\n  After normalization:   {len(normalized):>6,}")
    print(f"  Exact duplicates removed: {dedup_stats['exact_removed']:>4,}")
    print(f"  Near duplicates removed:  {dedup_stats['near_removed']:>4,}")
    print(f"\n  [OK] FINAL DATASET:     {len(final_records):>6,} reviews")
    print(f"\n  Output: {out_path}")
    print(f"  Summary: {summary_path}")
    print("=" * 60 + "\n")

    # Show source breakdown stats
    _show_stats(out_path)


if __name__ == "__main__":
    main()
