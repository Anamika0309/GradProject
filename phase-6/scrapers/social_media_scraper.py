"""
Phase 6 – Social Media Scraper (YouTube Comments)
===================================================
Scrapes comments from high-engagement Spotify-related YouTube videos
using the YouTube Data API v3 (free tier: 10,000 units/day).

Requires: YOUTUBE_API_KEY in config/.env

Target videos: Spotify Wrapped reactions, algorithm discussions,
               recommendation complaint videos, music discovery explainers.
Target: 1,500-2,000 comments
"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import json
import time
import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv(Path(__file__).parent.parent / "config" / ".env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [youtube] %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent / "storage" / "raw"
MIN_WORD_COUNT = 8
MAX_COMMENTS_PER_VIDEO = 300
SLEEP_BETWEEN_VIDEOS = 2.0

# Curated list of Spotify-related YouTube videos with high comment engagement.
# All IDs verified live via YouTube Search API - confirmed to have comments enabled.
TARGET_VIDEOS = [
    # Spotify recommendations & algorithm complaints
    {"id": "lnErNM7rjqg", "title": "Spotify is Getting Greedy Now!"},
    {"id": "pGntmcy_HX8", "title": "How Spotify AI-Driven Recommendations Work (WSJ)"},
    {"id": "-w3hk2KtKXo", "title": "We Cracked The Spotify Algorithm Again"},
    {"id": "jcbRyq14AEo", "title": "How Spotify Recommendations Work for 500M Users"},
    {"id": "-fc6argy4z4", "title": "Spotify Algorithm Works Like This"},
    {"id": "H-AVBZFjIZU", "title": "Spotify Algorithm Sucks"},
    {"id": "BaerSvM1BK4", "title": "Do Not Listen to Music on Spotify Until You Know This"},
    # Spotify vs Apple Music / discovery
    {"id": "r-EBS023zDk", "title": "Spotify vs Apple Music"},
    {"id": "-98LKRfnrnU", "title": "Spotify vs Apple Music vs YouTube Music"},
    {"id": "JPXgCGaqreA", "title": "I Switched From Spotify To Apple Music"},
    {"id": "aPar3BMd45Q", "title": "Spotify VS Apple Music Who WINS"},
    # Discover Weekly
    {"id": "N_U4tEh9p_8", "title": "The Science Behind Spotify Discover Weekly"},
    {"id": "PfdH5ytH2NQ", "title": "How We Triggered Discover Weekly"},
    {"id": "IcTM_XENfaE", "title": "How to BLOW UP on Discover Weekly"},
    # Spotify Wrapped reactions
    {"id": "oKC-FhSTNX4", "title": "Spotify Wrapped 2024 Minutes Listened"},
    {"id": "Lm8rRkpFdX0", "title": "Your Spotify Wrapped Isnt Good"},
    {"id": "9z2HsmsW2pI", "title": "Worst of Spotify Wrapped 2024"},
    # Same songs / fix guides
    {"id": "rAwi4eR97eA", "title": "How to Fix Spotify Playing the Same Songs"},
    {"id": "ZP-JqVgCLOI", "title": "How To Fix Spotify Playing Random Songs"},
    # Features & tips
    {"id": "y5rNcdqDRTk", "title": "Spotify Most Underrated Feature"},
]


def generate_id(video_id: str, comment_id: str) -> str:
    raw = f"youtube_{video_id}_{comment_id}"
    return "yt_" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_youtube_client():
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "YouTube API key not found. Add YOUTUBE_API_KEY to config/.env. "
            "Get a free key at: https://console.cloud.google.com → YouTube Data API v3."
        )
    return build("youtube", "v3", developerKey=api_key)


def fetch_video_comments(youtube, video_id: str, max_comments: int) -> list[dict]:
    """Fetch top-level comments (with replies count) for a YouTube video."""
    comments = []
    next_page_token = None

    try:
        while len(comments) < max_comments:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(100, max_comments - len(comments)),
                order="relevance",
                textFormat="plainText",
                pageToken=next_page_token,
            )
            response = request.execute()
            items = response.get("items", [])

            for item in items:
                snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                comments.append({
                    "id": item.get("id", ""),
                    "text": snippet.get("textDisplay", ""),
                    "author": snippet.get("authorDisplayName", "anonymous"),
                    "date": snippet.get("publishedAt", ""),
                    "like_count": snippet.get("likeCount", 0),
                    "reply_count": item.get("snippet", {}).get("totalReplyCount", 0),
                })

            next_page_token = response.get("nextPageToken")
            if not next_page_token or not items:
                break

    except HttpError as exc:
        if exc.resp.status == 403:
            logger.warning(f"  Comments disabled for video {video_id}: {exc}")
        elif exc.resp.status == 404:
            logger.warning(f"  Video not found: {video_id}")
        else:
            logger.warning(f"  YouTube API error for {video_id}: {exc}")

    return comments


def normalize_comment(raw: dict, video_id: str, video_title: str) -> dict | None:
    """Map YouTube raw comment → unified schema."""
    text = (raw.get("text") or "").strip()
    word_count = len(text.split())
    if word_count < MIN_WORD_COUNT:
        return None

    date_str = raw.get("date") or datetime.now(timezone.utc).isoformat()
    try:
        iso_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).isoformat()
    except Exception:
        iso_date = datetime.now(timezone.utc).isoformat()

    return {
        "id": generate_id(video_id, raw.get("id", hash(text).__str__())),
        "source": "social_media",
        "platform": "youtube",
        "text": text,
        "title": f"Comment on: {video_title[:80]}",
        "author": raw.get("author") or "anonymous",
        "date": iso_date,
        "rating": None,
        "language": "en",
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "word_count": word_count,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "score": None,
            "num_comments": None,
            "subreddit": None,
            "country": None,
            "video_id": video_id,
            "video_title": video_title,
            "like_count": raw.get("like_count", 0),
            "flair": None,
        },
    }


def run() -> list[dict]:
    """Run the full YouTube comment scrape across target videos."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Connecting to YouTube Data API v3…")
    try:
        youtube = get_youtube_client()
    except EnvironmentError as e:
        logger.error(str(e))
        return []

    all_records: list[dict] = []
    seen_ids: set[str] = set()

    for video in tqdm(TARGET_VIDEOS, desc="YouTube Videos", unit="video"):
        vid_id = video["id"]
        vid_title = video["title"]
        logger.info(f"  Fetching comments: {vid_title} (id: {vid_id})")

        raw_comments = fetch_video_comments(youtube, vid_id, MAX_COMMENTS_PER_VIDEO)
        logger.info(f"    Raw comments: {len(raw_comments)}")

        for raw in raw_comments:
            if raw["id"] in seen_ids:
                continue
            seen_ids.add(raw["id"])

            normalized = normalize_comment(raw, vid_id, vid_title)
            if normalized:
                all_records.append(normalized)

        time.sleep(SLEEP_BETWEEN_VIDEOS)

    logger.info(f"YouTube total after filtering: {len(all_records)} records")

    out_path = OUTPUT_DIR / "social_media_reviews.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved → {out_path}")

    return all_records


if __name__ == "__main__":
    results = run()
    print(f"\n[OK] YouTube scrape complete: {len(results)} comments saved.")
