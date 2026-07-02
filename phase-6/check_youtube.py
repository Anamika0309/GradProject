import json, sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open('storage/raw/social_media_reviews.json', encoding='utf-8') as f:
    data = json.load(f)

by_video = {}
for r in data:
    v = r.get('metadata', {}).get('video_title', 'unknown')[:50]
    by_video[v] = by_video.get(v, 0) + 1

print(f"Total YouTube comments: {len(data)}")
print(f"Source: {data[0]['source'] if data else 'N/A'}")
print(f"Platform: {data[0]['platform'] if data else 'N/A'}")
print(f"\nBy video:")
for title, count in sorted(by_video.items(), key=lambda x: -x[1]):
    print(f"  {count:>4}  {title}")
