"""
Phase 2 – Pre-LLM Data Strategy
=================================
Sits between Phase 6 scraped data and the Groq LLM.

Pipeline:
  1. Load the Phase 6 dataset (all_reviews.json)
  2. Filter noise (short reviews, non-English)
  3. Stratified sample across sources, ratings, and word lengths
  4. Compute a Python-side context summary (no LLM needed)
  5. Build the final prompt payload that fits within Groq's token limit

Usage:
  from data_strategy import DataStrategy
  ds = DataStrategy()
  payload = ds.prepare()
  # payload["sample_text"]    → concatenated review text for the LLM
  # payload["context_summary"] → dict of pre-computed statistics
  # payload["sample_reviews"]  → list of raw review dicts used
"""

import json
import math
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Defaults ───────────────────────────────────────────────────────────────────
WORDS_PER_TOKEN = 0.75
TARGET_SAMPLE_SIZE = 35
MAX_TOKEN_BUDGET = 2000

BASE_DIR = Path(__file__).parent.parent
DEFAULT_DATASET_PATH = BASE_DIR / "phase-6" / "storage" / "processed" / "all_reviews.json"
MIN_WORD_COUNT = 10          # Reviews shorter than this are noise
NEG_OVERSAMPLE_FACTOR = 1.5  # Oversample negative reviews by this multiplier


# ── Main Class ─────────────────────────────────────────────────────────────────

class DataStrategy:
    """Pre-LLM data preparation pipeline for the Product Insights Engine."""

    def __init__(self, dataset_path: Union[str, Path] = None, sample_size: int = 35):
        """
        Initialize the DataStrategy for pre-LLM dataset processing.
        sample_size defaults to 35 (approx 2,000 tokens) to stay strictly within 
        Groq's 12K Tokens Per Minute limit when running 4 parallel agents.
        """
        self.dataset_path = Path(dataset_path) if dataset_path else DEFAULT_DATASET_PATH
        self.sample_size = sample_size
        self._raw: List[Dict] = []
        self._filtered: List[Dict] = []
        self._sample: List[Dict] = []
        self._context: Dict[str, Any] = {}

    # ── Step 0: Load ───────────────────────────────────────────────────────────
    def load(self) -> "DataStrategy":
        """Load the Phase 6 processed dataset."""
        if not self.dataset_path.exists():
            raise FileNotFoundError(
                f"Dataset not found at {self.dataset_path}. "
                "Run the Phase 6 scraping pipeline first."
            )
        with open(self.dataset_path, encoding="utf-8") as f:
            self._raw = json.load(f)
        print(f"[DataStrategy] Loaded {len(self._raw):,} reviews from {self.dataset_path.name}")
        return self

    # ── Step 1: Filter Noise ───────────────────────────────────────────────────
    def filter_noise(self) -> "DataStrategy":
        """Remove reviews that are too short to contain useful product insights."""
        before = len(self._raw)
        self._filtered = [
            r for r in self._raw
            if r.get("word_count", 0) >= MIN_WORD_COUNT
            and r.get("language", "en") == "en"
            and r.get("text", "").strip()
        ]
        removed = before - len(self._filtered)
        print(f"[DataStrategy] Filtered noise: {before:,} → {len(self._filtered):,} ({removed} removed)")
        return self

    # ── Step 2: Stratified Sample ──────────────────────────────────────────────
    def stratified_sample(self) -> "DataStrategy":
        """
        Select a representative sample across sources and ratings.
        Over-samples negative reviews (1-2 stars) since they contain
        the richest pain points and unmet needs for PM analysis.
        """
        reviews = self._filtered if self._filtered else self._raw
        n = min(self.sample_size, len(reviews))

        # Group by source
        by_source: Dict[str, List[Dict]] = {}
        for r in reviews:
            src = r.get("source", "unknown")
            by_source.setdefault(src, []).append(r)

        # Calculate proportional allocation per source
        source_alloc: Dict[str, int] = {}
        for src, items in by_source.items():
            source_alloc[src] = max(1, round(len(items) / len(reviews) * n))

        # Adjust total to match target
        total_alloc = sum(source_alloc.values())
        if total_alloc != n:
            diff = n - total_alloc
            largest = max(source_alloc, key=source_alloc.get)
            source_alloc[largest] += diff

        selected = []
        for src, alloc in source_alloc.items():
            pool = by_source.get(src, [])
            if not pool:
                continue

            # Split into negative (1-2) and other
            neg = [r for r in pool if r.get("rating") is not None and r["rating"] <= 2]
            other = [r for r in pool if r not in neg]

            # Over-sample negatives
            neg_count = min(len(neg), round(alloc * NEG_OVERSAMPLE_FACTOR * 0.4))
            other_count = alloc - neg_count

            random.seed(42)  # Reproducible
            picked_neg = random.sample(neg, min(neg_count, len(neg)))
            picked_other = random.sample(other, min(other_count, len(other)))
            selected.extend(picked_neg)
            selected.extend(picked_other)

        # Deduplicate and trim
        seen_ids = set()
        unique = []
        for r in selected:
            rid = r.get("id", id(r))
            if rid not in seen_ids:
                seen_ids.add(rid)
                unique.append(r)

        self._sample = unique[:n]
        print(f"[DataStrategy] Sampled {len(self._sample)} reviews (target: {n})")

        # Log source breakdown
        sample_sources = Counter(r.get("source") for r in self._sample)
        for src, count in sample_sources.most_common():
            print(f"  → {src}: {count}")

        return self

    # ── Step 3: Context Summary ────────────────────────────────────────────────
    def compute_context_summary(self) -> "DataStrategy":
        """
        Compute statistics from the FULL dataset (not just the sample).
        These go into the LLM prompt as grounding data so the AI knows
        the big picture even though it only reads a subset of reviews.
        """
        all_reviews = self._filtered if self._filtered else self._raw

        # Rating distribution
        rating_dist = Counter()
        for r in all_reviews:
            rating = r.get("rating")
            if rating is not None:
                rating_dist[rating] += 1
            else:
                rating_dist["unrated"] += 1

        # Source distribution
        source_dist = Counter(r.get("source", "unknown") for r in all_reviews)

        # Word count stats
        word_counts = [r.get("word_count", 0) for r in all_reviews]

        # Top repeated words/phrases (simple TF)
        word_freq = Counter()
        # Stop words to exclude
        stop = {
            "the", "a", "an", "is", "it", "i", "to", "and", "of", "in",
            "for", "on", "my", "this", "that", "but", "with", "not", "you",
            "have", "was", "are", "so", "just", "can", "its", "been", "from",
            "they", "all", "very", "me", "be", "do", "no", "if", "would",
            "will", "about", "has", "had", "what", "when", "how", "or",
            "more", "one", "like", "get", "even", "really", "also", "use",
            "don't", "there", "than", "only", "some", "much", "too", "now",
            "because", "up", "out", "at", "am", "we", "as", "by", "your",
            "app", "spotify", "music",  # domain-common, not informative
        }
        for r in all_reviews:
            text = r.get("text", "").lower()
            words = re.findall(r"[a-z']+", text)
            for w in words:
                if len(w) > 2 and w not in stop:
                    word_freq[w] += 1

        # Sentiment proxy from ratings
        rated = [r for r in all_reviews if r.get("rating") is not None]
        positive = sum(1 for r in rated if r["rating"] >= 4)
        negative = sum(1 for r in rated if r["rating"] <= 2)
        neutral = sum(1 for r in rated if r["rating"] == 3)

        self._context = {
            "total_reviews_in_dataset": len(all_reviews),
            "total_reviews_in_sample": len(self._sample),
            "source_distribution": dict(source_dist.most_common()),
            "rating_distribution": {
                str(k): v for k, v in sorted(rating_dist.items(), key=lambda x: str(x[0]))
            },
            "sentiment_proxy": {
                "positive_4_5_stars": positive,
                "neutral_3_stars": neutral,
                "negative_1_2_stars": negative,
                "unrated": rating_dist.get("unrated", 0),
            },
            "word_count_stats": {
                "average": round(sum(word_counts) / max(len(word_counts), 1), 1),
                "min": min(word_counts) if word_counts else 0,
                "max": max(word_counts) if word_counts else 0,
            },
            "top_keywords": [
                {"word": w, "count": c}
                for w, c in word_freq.most_common(30)
            ],
        }

        print(f"[DataStrategy] Context summary computed ({len(self._context['top_keywords'])} top keywords)")
        return self

    # ── Step 4: Build LLM Payload ──────────────────────────────────────────────
    def build_payload(self) -> Dict[str, Any]:
        """
        Format the sampled reviews and context summary into a payload
        ready for the Groq LLM. Stays within MAX_TOKEN_BUDGET.
        """
        # Build the context block
        context_text = (
            "=== DATASET CONTEXT (computed from full dataset) ===\n"
            f"Total reviews in full dataset: {self._context['total_reviews_in_dataset']:,}\n"
            f"Reviews in this sample: {self._context['total_reviews_in_sample']}\n"
            f"Source distribution: {json.dumps(self._context['source_distribution'])}\n"
            f"Rating distribution: {json.dumps(self._context['rating_distribution'])}\n"
            f"Sentiment proxy: {json.dumps(self._context['sentiment_proxy'])}\n"
            f"Avg word count: {self._context['word_count_stats']['average']}\n"
            f"Top keywords: {', '.join(kw['word'] for kw in self._context['top_keywords'][:20])}\n"
            "=== END CONTEXT ===\n\n"
        )

        # Build the reviews block
        review_lines = []
        est_tokens = len(context_text.split()) / WORDS_PER_TOKEN
        for i, r in enumerate(self._sample):
            text = r.get("text", "").strip()
            source = r.get("source", "?")
            rating = r.get("rating")
            rating_str = f" | {rating}★" if rating else ""

            line = f"[Review {i+1} | {source}{rating_str}]\n{text}\n"
            line_tokens = len(line.split()) / WORDS_PER_TOKEN

            if est_tokens + line_tokens > MAX_TOKEN_BUDGET:
                print(f"[DataStrategy] Token budget reached at review {i+1}, truncating.")
                break

            review_lines.append(line)
            est_tokens += line_tokens

        sample_text = context_text + "=== SAMPLED REVIEWS ===\n\n" + "\n".join(review_lines)

        print(f"[DataStrategy] Payload built: ~{int(est_tokens):,} est. tokens, {len(review_lines)} reviews included")

        return {
            "sample_text": sample_text,
            "context_summary": self._context,
            "sample_reviews": self._sample[:len(review_lines)],
            "estimated_tokens": int(est_tokens),
            "reviews_included": len(review_lines),
        }

    def prepare(self) -> Dict[str, Any]:
        """
        Main execution method for single-chunk analysis.
        Loads data, filters noise, samples to `sample_size`, computes context,
        and builds the final payload.
        """
        self.load()
        self.filter_noise()
        self.stratified_sample()
        self.compute_context_summary()
        return self.build_payload()

    def prepare_chunks(self, chunk_size: int = 100) -> List[Dict[str, Any]]:
        """
        Prepare multiple chunk payloads for Map-Reduce analysis.
        If self.sample_size > chunk_size, it splits the dataset into multiple payloads.
        """
        self.load()
        self.filter_noise()
        self.stratified_sample()
        self.compute_context_summary()

        # Split self._sample into chunks
        chunks = [self._sample[i:i + chunk_size] for i in range(0, len(self._sample), chunk_size)]
        
        payloads = []
        for c in chunks:
            self._sample = c  # Temporarily override sample to build payload for this chunk
            payloads.append(self.build_payload())
            
        print(f"[DataStrategy] Prepared {len(payloads)} chunks for map-reduce analysis.")
        return payloads

# ── Standalone Test ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  Data Strategy – Standalone Test")
    print("=" * 60)

    ds = DataStrategy()
    payload = ds.prepare()

    print(f"\n{'='*60}")
    print(f"  RESULT SUMMARY")
    print(f"{'='*60}")
    print(f"  Reviews included:    {payload['reviews_included']}")
    print(f"  Estimated tokens:    {payload['estimated_tokens']:,}")
    print(f"  Context keys:        {list(payload['context_summary'].keys())}")
    print(f"  Sample text length:  {len(payload['sample_text']):,} chars")
    print(f"\n  Top 10 keywords:")
    for kw in payload["context_summary"]["top_keywords"][:10]:
        print(f"    {kw['word']:<20} ({kw['count']})")
    print(f"{'='*60}")
