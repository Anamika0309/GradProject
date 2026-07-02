import os
import sys
import json
import time

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "phase-2"))
from data_strategy import DataStrategy
from agents import ReviewAnalysisPipeline, AgentConfig
from groq import Groq

# Use 105 reviews so it makes 2 chunks (100 and 5) and triggers map-reduce
ds = DataStrategy(dataset_path="phase-6/data/all_reviews.json", sample_size=105)
payloads = ds.prepare_chunks(chunk_size=100)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
pipeline = ReviewAnalysisPipeline(client=client, model="llama-3.3-70b-versatile")

print("Starting pipeline...")
res = pipeline.analyze_chunked_dataset(payloads)

# Save result to a file for easy viewing
output_file = "scratch/map_reduce_output.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2, ensure_ascii=False)

print(f"\nDone! Output saved to {output_file}")
