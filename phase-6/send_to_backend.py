import json
import requests
import os
import sys

# Load all collected reviews
REVIEWS_FILE = "phase-6/storage/processed/all_reviews.json"
if not os.path.exists(REVIEWS_FILE):
    print(f"Error: {REVIEWS_FILE} not found. Ensure Phase 6 scraper finished.")
    sys.exit(1)

with open(REVIEWS_FILE, "r", encoding="utf-8") as f:
    reviews = json.load(f)

print(f"Loaded {len(reviews)} deduplicated reviews.", flush=True)

# Map-Reduce Backend URL
WEBHOOK_URL = "http://localhost:5678/webhook/analyze-dataset"
# For this demo, let's take a sample of 150 reviews
SAMPLE_SIZE = 150
print(f"Sending sample of {SAMPLE_SIZE} reviews to backend...", flush=True)

# Send request
payload = {
    "sample_size": SAMPLE_SIZE,
    "filepath": os.path.abspath(REVIEWS_FILE)
}

print("Initiating Map-Reduce pipeline... This will take a couple of minutes...", flush=True)
resp = requests.post(WEBHOOK_URL, json=payload, timeout=600)

if resp.status_code == 200:
    print("\n[OK] MAP-REDUCE COMPLETE! [OK]\n")
    data = resp.json()
    print("Executive Summary:\n", data.get("executive_summary", "No summary provided"))
    print("\nCheck localhost:8000 to see the beautiful UI rendering!")
    
    # Save the huge payload
    with open("phase-6/storage/processed/ai_insights.json", "w", encoding="utf-8") as out:
        json.dump(data, out, indent=2)
else:
    print(f"[FAIL] Failed! Status: {resp.status_code}")
    print(resp.text)
