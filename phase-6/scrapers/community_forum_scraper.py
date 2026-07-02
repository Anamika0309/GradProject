"""
Phase 6 – Spotify Community Forum Scraper
==========================================
Scrapes posts from the Spotify Community forum (community.spotify.com)
using Playwright (headless Chromium) + BeautifulSoup.

Targets boards:
  - Ideas  (feature requests, community votes)
  - Help   (user problems, frustrations)
  - Music & Podcasts (listening discussions)

Target: 500–1,000 posts
No credentials required (public forum).
"""

import json
import time
import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from tqdm import tqdm

# Playwright is imported inside functions so the module can still be imported
# even if Playwright is not installed (graceful fallback)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [forum] %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent / "storage" / "raw"
MIN_WORD_COUNT = 10
PAGE_DELAY = 2.5          # Seconds between page requests (respectful)
MAX_PAGES_PER_BOARD = 20  # Pages of thread listings per board

BASE_URL = "https://community.spotify.com"

# Forum boards to scrape (board path → display name)
BOARDS = {
    "/t5/Ongoing-Issues/bd-p/ongoing": "Ongoing Issues",
    "/t5/Ideas/bd-p/ideas": "Ideas",
    "/t5/Help/bd-p/help": "Help",
}


def generate_id(url: str) -> str:
    return "cf_" + hashlib.sha256(url.encode()).hexdigest()[:16]


def parse_date(date_str: str | None) -> str:
    """Parse Lithium forum date string to ISO 8601."""
    if not date_str:
        return datetime.now(timezone.utc).isoformat()
    try:
        # Lithium typically uses format: "2024-05-10T08:30:00.000+0000"
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def get_thread_urls(page, board_path: str) -> list[str]:
    """Get all thread URLs from a board listing page."""
    urls = []
    try:
        html = page.content()
        soup = BeautifulSoup(html, "lxml")

        # Lithium CMS uses these selectors (common across Spotify Community)
        # Try multiple selectors for resilience
        selectors = [
            "a.page-link.lia-link-navigation.lia-custom-event",
            "h2.lia-message-subject a",
            "a[href*='/t5/'][href*='/m-p/']",
            "a[href*='/t5/'][href*='/td-p/']",
        ]

        for selector in selectors:
            links = soup.select(selector)
            if links:
                for link in links:
                    href = link.get("href", "")
                    if href and "/t5/" in href and href not in urls:
                        full_url = urljoin(BASE_URL, href)
                        urls.append(full_url)
                break

    except Exception as exc:
        logger.debug(f"Error parsing board page: {exc}")

    return urls


def scrape_thread(page, thread_url: str, board_name: str) -> list[dict]:
    """Scrape all posts from a single forum thread."""
    records = []
    try:
        page.goto(thread_url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(1.5)
        html = page.content()
        soup = BeautifulSoup(html, "lxml")

        # Thread title
        title_el = soup.select_one("h1.lia-message-subject-banner, h1.page-title, h1")
        title = title_el.get_text(strip=True) if title_el else "Unknown Title"

        # All post bodies in the thread
        post_selectors = [
            "div.lia-message-body-content",
            "div.MessageBody",
            "div[class*='message-body']",
        ]

        posts_found = []
        for sel in post_selectors:
            posts_found = soup.select(sel)
            if posts_found:
                break

        if not posts_found:
            # Fallback: grab all <p> tags inside article-like containers
            posts_found = soup.select("article p, .post p")

        for i, post_el in enumerate(posts_found):
            text = post_el.get_text(separator=" ", strip=True)
            text = re.sub(r"\s+", " ", text).strip()
            word_count = len(text.split())

            if word_count < MIN_WORD_COUNT:
                continue

            # Try to get author
            author_el = post_el.find_parent().find(
                "a", class_=re.compile(r"lia-user-name|UserName|author", re.I)
            ) if post_el.find_parent() else None
            author = author_el.get_text(strip=True) if author_el else "community_user"

            # Try to get date
            date_el = post_el.find_parent().find(
                "span", class_=re.compile(r"local-date|post-date|timestamp", re.I)
            ) if post_el.find_parent() else None
            date_str = date_el.get("data-date", "") if date_el else ""
            iso_date = parse_date(date_str)

            record = {
                "id": generate_id(f"{thread_url}_{i}"),
                "source": "community_forum",
                "platform": "spotify_community",
                "text": text,
                "title": title if i == 0 else f"Reply in: {title[:60]}",
                "author": author,
                "date": iso_date,
                "rating": None,
                "language": "en",
                "url": thread_url,
                "word_count": word_count,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "score": None,
                    "num_comments": len(posts_found),
                    "subreddit": None,
                    "country": None,
                    "video_id": None,
                    "video_title": None,
                    "like_count": None,
                    "flair": board_name,
                },
            }
            records.append(record)

    except Exception as exc:
        logger.debug(f"Failed to scrape thread {thread_url}: {exc}")

    return records


def run() -> list[dict]:
    """Run the full Spotify Community Forum scrape."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error(
            "Playwright not installed. Run: pip install playwright && playwright install chromium"
        )
        return []

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_records: list[dict] = []
    seen_urls: set[str] = set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        for board_path, board_name in BOARDS.items():
            logger.info(f"Crawling board: {board_name}")
            thread_urls: list[str] = []

            # Paginate through board listing
            for page_num in range(1, MAX_PAGES_PER_BOARD + 1):
                # Lithium pagination uses /page/<N> suffix
                listing_url = f"{BASE_URL}{board_path}/page/{page_num}"
                try:
                    page.goto(listing_url, wait_until="domcontentloaded", timeout=25000)
                    time.sleep(PAGE_DELAY)
                    new_urls = get_thread_urls(page, board_path)
                    if not new_urls:
                        logger.info(f"  No more threads at page {page_num}, stopping.")
                        break
                    thread_urls.extend(u for u in new_urls if u not in seen_urls)
                    logger.info(f"  Page {page_num}: found {len(new_urls)} threads")
                except Exception as exc:
                    logger.warning(f"  Board listing error (page {page_num}): {exc}")
                    break

            logger.info(f"  Total threads to scrape for [{board_name}]: {len(thread_urls)}")

            # Scrape each thread
            for url in tqdm(thread_urls, desc=f"Forum [{board_name}]", unit="thread"):
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                thread_records = scrape_thread(page, url, board_name)
                all_records.extend(thread_records)
                time.sleep(PAGE_DELAY)

        browser.close()

    logger.info(f"Community Forum total: {len(all_records)} records")

    out_path = OUTPUT_DIR / "forum_reviews.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved → {out_path}")

    return all_records


if __name__ == "__main__":
    results = run()
    print(f"\n✅  Community Forum scrape complete: {len(results)} records saved.")
