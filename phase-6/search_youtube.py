"""Script to find valid Spotify-related YouTube video IDs."""
import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('config/.env')

key = os.getenv('YOUTUBE_API_KEY', '')
from googleapiclient.discovery import build

youtube = build('youtube', 'v3', developerKey=key)

queries = [
    'spotify recommendations broken 2024',
    'spotify algorithm explained music',
    'spotify vs apple music discovery feature',
    'spotify discover weekly how it works',
    'spotify wrapped 2024 reaction',
    'why spotify keeps playing same songs',
    'spotify playlist algorithm complaints',
    'spotify music discovery tips',
]

found_videos = []
seen_ids = set()

for q in queries:
    req = youtube.search().list(
        part='snippet',
        q=q,
        type='video',
        maxResults=4,
        order='relevance',
        relevanceLanguage='en',
        fields='items(id(videoId),snippet(title,channelTitle))'
    )
    resp = req.execute()
    count = len(resp.get('items', []))
    print(f'Query [{q}] -> {count} results')
    for item in resp.get('items', []):
        vid_id = item['id']['videoId']
        title = item['snippet']['title']
        channel = item['snippet']['channelTitle']
        if vid_id not in seen_ids:
            seen_ids.add(vid_id)
            found_videos.append((vid_id, title, channel))

# Verify comments are enabled on these videos
print(f'\nVerifying {len(found_videos)} unique videos for comments...')
for vid_id, title, channel in found_videos:
    try:
        req = youtube.commentThreads().list(
            part='snippet',
            videoId=vid_id,
            maxResults=2,
            textFormat='plainText'
        )
        resp = req.execute()
        items = resp.get('items', [])
        print(f'  OK  {vid_id} | {title[:55]} | {len(items)} comments sample')
    except Exception as e:
        print(f'  SKIP {vid_id} | {title[:55]} | {str(e)[:60]}')
