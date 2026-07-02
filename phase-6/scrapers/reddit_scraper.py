"""
Phase 6 – Reddit Scraper
==========================
Scrapes Spotify-related posts and comments from 7 subreddits using PRAW.
Requires free Reddit API credentials (see config/config.example.env).

Target: 3,000–5,000 posts + comments
"""

import json
import time
import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import praw
from dotenv import load_dotenv
from tqdm import tqdm

# ── Configuration ──────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent.parent / "config" / ".env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [reddit] %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent / "storage" / "raw"
MIN_WORD_COUNT = 10
MAX_POSTS_PER_LISTING = 500   # hot/top/new per subreddit

# Target subreddits — all public, high engagement, music-discovery focused
SUBREDDITS = [
    "spotify",
    "Music",
    "audiophile",
    "spotifyplaylist",
    "ifyoulikeblank",
    "musicsuggestions",
    "AppleMusic",          # comparative reviews mention Spotify's weaknesses
]

# Keywords that indicate discovery-relevant content
DISCOVERY_KEYWORDS = {
    "recommend", "discover", "discovery", "playlist", "suggestion",
    "algorithm", "repeat", "repetitive", "boring", "shuffle",
    "new music", "find music", "similar", "genre", "listening",
    "frustrated", "broken", "hate", "love", "feature", "missing",
    "want", "need", "request", "improvement", "better", "worse",
}


def _is_relevant(text: str) -> bool:
    """Return True if the text contains at least one discovery-related keyword."""
    lower = text.lower()
    return any(kw in lower for kw in DISCOVERY_KEYWORDS)


def generate_id(item_id: str) -> str:
    raw = f"reddit_{item_id}"
    return "rd_" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_reddit_client() -> praw.Reddit:
    client_id = os.getenv("REDDIT_CLIENT_ID", "")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
    user_agent = os.getenv("REDDIT_USER_AGENT", "SpotifyReviewEngine/1.0")

    if not client_id or not client_secret:
        raise EnvironmentError(
            "Reddit credentials not found. Copy config/config.example.env → config/.env "
            "and fill in REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET."
        )

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )


def normalize_post(post, subreddit_name: str) -> dict | None:
    """Convert a PRAW Submission → unified schema."""
    text = (post.selftext or "").strip()
    title = (post.title or "").strip()
    full_text = f"{title}. {text}".strip() if text else title

    word_count = len(full_text.split())
    if word_count < MIN_WORD_COUNT:
        return None
    if not _is_relevant(full_text):
        return None

    created = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)

    return {
        "id": generate_id(post.id),
        "source": "reddit",
        "platform": f"r/{subreddit_name}",
        "text": full_text,
        "title": title or None,
        "author": str(post.author) if post.author else "anonymous",
        "date": created.isoformat(),
        "rating": None,
        "language": "en",
        "url": f"https://reddit.com{post.permalink}",
        "word_count": word_count,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "score": post.score,
            "num_comments": post.num_comments,
            "subreddit": f"r/{subreddit_name}",
            "country": None,
            "video_id": None,
            "video_title": None,
            "like_count": post.score,
            "flair": post.link_flair_text,
        },
    }


def normalize_comment(comment, subreddit_name: str, post_title: str) -> dict | None:
    """Convert a PRAW Comment → unified schema."""
    text = (comment.body or "").strip()
    if text in ("[deleted]", "[removed]", ""):
        return None

    full_text = text
    word_count = len(full_text.split())
    if word_count < MIN_WORD_COUNT:
        return None
    if not _is_relevant(full_text):
        return None

    created = datetime.fromtimestamp(comment.created_utc, tz=timezone.utc)

    return {
        "id": generate_id(comment.id),
        "source": "reddit",
        "platform": f"r/{subreddit_name}",
        "text": full_text,
        "title": f"Comment on: {post_title[:80]}",
        "author": str(comment.author) if comment.author else "anonymous",
        "date": created.isoformat(),
        "rating": None,
        "language": "en",
        "url": f"https://reddit.com{comment.permalink}",
        "word_count": word_count,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "score": comment.score,
            "num_comments": None,
            "subreddit": f"r/{subreddit_name}",
            "country": None,
            "video_id": None,
            "video_title": None,
            "like_count": comment.score,
            "flair": None,
        },
    }


def scrape_subreddit(reddit: praw.Reddit, sub_name: str) -> list[dict]:
    """Scrape posts (hot + top + new) and their comments from one subreddit."""
    records = []
    seen_ids: set[str] = set()
    subreddit = reddit.subreddit(sub_name)

    listings = [
        ("hot", subreddit.hot(limit=MAX_POSTS_PER_LISTING)),
        ("top", subreddit.top(time_filter="year", limit=MAX_POSTS_PER_LISTING)),
        ("new", subreddit.new(limit=MAX_POSTS_PER_LISTING)),
    ]

    for listing_name, listing in listings:
        logger.info(f"  r/{sub_name} [{listing_name}]…")
        posts = list(tqdm(listing, desc=f"  r/{sub_name}/{listing_name}", unit="post", leave=False))

        for post in posts:
            if post.id in seen_ids:
                continue
            seen_ids.add(post.id)

            # Normalize and store the post itself
            post_record = normalize_post(post, sub_name)
            if post_record:
                records.append(post_record)

            # Scrape top-level comments for posts with meaningful engagement
            if post.num_comments > 3 and _is_relevant(post.title):
                try:
                    post.comments.replace_more(limit=0)  # Don't load MoreComments
                    for comment in post.comments.list()[:30]:  # Max 30 comments per post
                        if comment.id in seen_ids:
                            continue
                        seen_ids.add(comment.id)
                        comment_record = normalize_comment(comment, sub_name, post.title)
                        if comment_record:
                            records.append(comment_record)
                except Exception as exc:
                    logger.debug(f"    Comment fetch error: {exc}")

            time.sleep(0.1)  # Gentle pacing

    logger.info(f"  r/{sub_name}: {len(records)} relevant records")
    return records


def run() -> list[dict]:
    """Run the full Reddit scrape across all subreddits."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Connecting to Reddit API…")
    try:
        reddit = get_reddit_client()
        # Verify credentials with a lightweight call
        _ = reddit.user.me()
        logger.info("Reddit authentication successful.")
    except EnvironmentError as e:
        logger.error(str(e))
        return []
    except Exception as exc:
        # read-only mode also works for public data
        logger.warning(f"Auth note: {exc}. Continuing in read-only mode.")

    all_records: list[dict] = []
    for sub_name in SUBREDDITS:
        try:
            sub_records = scrape_subreddit(reddit, sub_name)
            all_records.extend(sub_records)
        except Exception as exc:
            logger.warning(f"Skipping r/{sub_name}: {exc}")
        time.sleep(2)

    logger.info(f"Reddit total: {len(all_records)} records")

    out_path = OUTPUT_DIR / "reddit_reviews.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved → {out_path}")

    return all_records


if __name__ == "__main__":
    results = run()
    print(f"\n✅  Reddit scrape complete: {len(results)} records saved.")
