import json, re, sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EMOJI = re.compile(
    "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
    "\U0001F900-\U0001F9FF\U00002702-\U000027B0\U00002600-\U00002B55]+",
    flags=re.UNICODE
)

with open("storage/processed/all_reviews.json", encoding="utf-8") as f:
    data = json.load(f)

ps = [r for r in data if r.get("source") == "play_store"]
with_emoji = [r for r in ps if EMOJI.search(r.get("text", ""))]

print(f"Play Store reviews in final output: {len(ps)}")
print(f"Still contain emojis: {len(with_emoji)}")

if with_emoji:
    sample = with_emoji[0]["text"][:150]
    print(f"Sample with emoji: {sample}")
else:
    # Show a cleaned sample
    raw_sample = ps[0]["text"][:150] if ps else "N/A"
    print(f"All clean! Sample: {raw_sample}")
