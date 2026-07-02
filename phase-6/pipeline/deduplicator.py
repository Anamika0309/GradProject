"""
Phase 6 – Deduplicator
========================
Removes exact and near-duplicate reviews across all sources.

Strategy:
  1. Exact dedup: same `id` or identical `text` hash
  2. Near-dedup: text similarity ≥ 85% (using simple Jaccard on word sets)

Near-dedup is optional — it's slower on large datasets but catches
cross-posted reviews (same text on App Store and Reddit, for example).
"""

import json
import hashlib
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [dedup] %(message)s")
logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.85  # Jaccard similarity above this = near-duplicate


def text_fingerprint(text: str) -> str:
    """SHA-256 of lowercase stripped text (exact duplicate detection)."""
    return hashlib.sha256(text.lower().strip().encode()).hexdigest()


def jaccard_similarity(text_a: str, text_b: str) -> float:
    """Word-level Jaccard similarity between two texts."""
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def deduplicate_exact(records: list[dict]) -> tuple[list[dict], int]:
    """
    Remove records with identical IDs or identical text content.
    O(n) — safe for large datasets.
    """
    seen_ids: set[str] = set()
    seen_fingerprints: set[str] = set()
    unique: list[dict] = []
    removed = 0

    for record in records:
        rid = record.get("id", "")
        fp = text_fingerprint(record.get("text", ""))

        if rid in seen_ids or fp in seen_fingerprints:
            removed += 1
            continue

        seen_ids.add(rid)
        seen_fingerprints.add(fp)
        unique.append(record)

    return unique, removed


def deduplicate_near(records: list[dict], threshold: float = SIMILARITY_THRESHOLD) -> tuple[list[dict], int]:
    """
    Remove near-duplicate records using Jaccard similarity.
    O(n²) — only run on smaller datasets or after exact dedup.
    For datasets > 5,000 records this may take a minute.
    """
    logger.info(f"Running near-dedup on {len(records)} records (threshold={threshold})…")

    unique: list[dict] = []
    removed = 0

    # Use word sets for fast comparison
    word_sets = [set(r["text"].lower().split()) for r in records]

    for i, record in enumerate(records):
        is_dup = False
        set_i = word_sets[i]

        for j in range(i):
            set_j = word_sets[j]
            intersection = set_i & set_j
            union = set_i | set_j
            if union and len(intersection) / len(union) >= threshold:
                is_dup = True
                break

        if is_dup:
            removed += 1
        else:
            unique.append(record)

    return unique, removed


def run_deduplication(
    records: list[dict],
    near_dedup: bool = True,
) -> tuple[list[dict], dict]:
    """
    Full deduplication pipeline.
    Returns (deduplicated_records, stats_dict).
    """
    original_count = len(records)

    # Step 1: Exact dedup (always run)
    records, exact_removed = deduplicate_exact(records)
    logger.info(f"Exact dedup: removed {exact_removed} records ({len(records)} remain)")

    # Step 2: Near-dedup (optional, skip if dataset is very large)
    near_removed = 0
    if near_dedup:
        if len(records) > 8000:
            logger.warning(
                f"Dataset has {len(records)} records — skipping near-dedup for performance. "
                "Run with near_dedup=False or reduce dataset size."
            )
        else:
            records, near_removed = deduplicate_near(records)
            logger.info(f"Near dedup: removed {near_removed} records ({len(records)} remain)")

    stats = {
        "original": original_count,
        "exact_removed": exact_removed,
        "near_removed": near_removed,
        "final_count": len(records),
        "reduction_pct": round((original_count - len(records)) / max(original_count, 1) * 100, 1),
    }

    logger.info(
        f"Deduplication complete: {original_count} → {len(records)} "
        f"({stats['reduction_pct']}% reduction)"
    )
    return records, stats
