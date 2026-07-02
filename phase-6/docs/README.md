# Phase 6 – Real Review Scraping at Scale

Collects **6,000–13,000+ real Spotify reviews** from 5 sources and feeds them into the AI agent pipeline.

---

## Sources & Expected Volume

| Source | Method | Target |
|---|---|---|
| App Store (US/UK/AU/CA/IN) | `app-store-scraper` | ~2,000 reviews |
| Google Play Store | `google-play-scraper` + pagination | ~3,000 reviews |
| Reddit (7 subreddits) | PRAW Official API | ~3,000–5,000 posts/comments |
| Spotify Community Forum | Playwright + BeautifulSoup | ~500–1,000 posts |
| YouTube Comments (social) | YouTube Data API v3 | ~1,500 comments |
| **Total (after dedup)** | | **~6,000–13,000** |

---

## Setup

### 1. Install dependencies

```bash
cd phase-6
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure API credentials

```bash
cp config/config.example.env config/.env
```

Then edit `config/.env` and fill in:

#### Reddit (FREE – 2 minutes)
1. Go to https://www.reddit.com/prefs/apps
2. Click **Create App** → choose type: **script**
3. Name: `SpotifyReviewEngine`, redirect: `http://localhost:8080`
4. Copy the **client_id** (under app name) and **client_secret**

#### YouTube Data API v3 (FREE)
1. Go to https://console.cloud.google.com
2. Create a new project → **Enable "YouTube Data API v3"**
3. Credentials → **Create API Key**
4. Paste the key into `.env`

> App Store and Play Store scrapers require **no API keys**.  
> Community Forum scraper requires **no API keys** (public Playwright scrape).

---

## Running the Scraper

### Check credentials (dry-run)
```bash
python pipeline/orchestrator.py --dry-run
```

### Scrape all sources
```bash
python pipeline/orchestrator.py
```

### Scrape specific sources only
```bash
python pipeline/orchestrator.py --sources app_store play_store
python pipeline/orchestrator.py --sources reddit
python pipeline/orchestrator.py --sources social_media
```

### Skip slow near-dedup (faster for large datasets)
```bash
python pipeline/orchestrator.py --no-near-dedup
```

### Show stats on existing dataset
```bash
python pipeline/orchestrator.py --stats
```

---

## Output Files

```
storage/
  raw/
    app_store_reviews.json       ← Raw App Store output
    play_store_reviews.json      ← Raw Play Store output
    reddit_reviews.json          ← Raw Reddit output
    forum_reviews.json           ← Raw Spotify Community output
    social_media_reviews.json    ← Raw YouTube output
  processed/
    all_reviews.json             ← Final merged + deduplicated dataset ★
    run_summary.json             ← Stats for the last run
  orchestrator.log               ← Full run log
```

---

## Unified Review Schema

Every review (regardless of source) is stored as:

```json
{
  "id": "rd_a1b2c3d4e5f6g7h8",
  "source": "reddit",
  "platform": "r/spotify",
  "text": "Discover Weekly has been recommending the same 10 artists for months...",
  "title": "Why is Discover Weekly so repetitive?",
  "author": "u/musicfan_xyz",
  "date": "2024-11-12T18:30:00+00:00",
  "rating": null,
  "language": "en",
  "url": "https://reddit.com/r/spotify/comments/abc123",
  "word_count": 47,
  "scraped_at": "2026-07-01T01:00:00+00:00",
  "metadata": {
    "score": 847,
    "num_comments": 132,
    "subreddit": "r/spotify",
    "country": null,
    "video_id": null,
    "video_title": null,
    "like_count": 847,
    "flair": "Discussion"
  }
}
```

---

## Running Individual Scrapers

You can also run each scraper standalone:

```bash
python scrapers/app_store_scraper.py
python scrapers/play_store_scraper.py
python scrapers/reddit_scraper.py
python scrapers/community_forum_scraper.py
python scrapers/social_media_scraper.py
```

---

## Integration with AI Pipeline (Phase 2)

The final `all_reviews.json` feeds the Phase 2 multi-agent pipeline in batches:

```python
import json, requests

with open("storage/processed/all_reviews.json") as f:
    reviews = json.load(f)

# Send batches of 50 to the backend API endpoint
BATCH_SIZE = 50
WEBHOOK = "http://localhost:5678/webhook/analyze"

for i in range(0, len(reviews), BATCH_SIZE):
    batch = reviews[i:i+BATCH_SIZE]
    combined_text = "\n\n---\n\n".join(r["text"] for r in batch)
    resp = requests.post(WEBHOOK, json={"reviews": combined_text})
    print(f"Batch {i//BATCH_SIZE + 1}: {resp.status_code}")
```

---

## Phase 6 Success Criteria

- [ ] `storage/raw/app_store_reviews.json` — ≥ 1,000 entries
- [ ] `storage/raw/play_store_reviews.json` — ≥ 1,500 entries
- [ ] `storage/raw/reddit_reviews.json` — ≥ 2,000 entries
- [ ] `storage/raw/forum_reviews.json` — ≥ 300 entries
- [ ] `storage/raw/social_media_reviews.json` — ≥ 500 entries
- [ ] `storage/processed/all_reviews.json` — ≥ 5,000 deduplicated reviews
- [ ] All entries have `text`, `source`, `date`, `id` fields
- [ ] Deduplication report shows < 15% reduction (minimal cross-posting)
- [ ] Sample 20 random reviews — all are real, English, Spotify-related

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `429 Too Many Requests` (Play Store) | Increase `SLEEP_BETWEEN_BATCHES` in play_store_scraper.py |
| `EnvironmentError: Reddit credentials` | Fill in `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` in config/.env |
| `EnvironmentError: YouTube API key` | Fill in `YOUTUBE_API_KEY` in config/.env |
| `playwright install chromium` fails | Run `playwright install` as admin, or use `python -m playwright install chromium` |
| Forum scraper returns 0 posts | Spotify may have updated their forum CSS — check selectors in community_forum_scraper.py |
| `langdetect` import error | Run `pip install langdetect` separately |
