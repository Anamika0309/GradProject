import sys
sys.path.append("phase-2")
import os
import json
from data_strategy import DataStrategy
from agents import ReviewAnalysisPipeline, AgentConfig
from groq import Groq
from dotenv import load_dotenv

load_dotenv("phase-6/config/.env")
ds = DataStrategy(sample_size=105)
payloads = ds.prepare_chunks(chunk_size=100)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
pipeline = ReviewAnalysisPipeline(client=client, model="llama-3.3-70b-versatile")
res = pipeline.analyze_chunked_dataset(payloads)
with open("C:/Users/Admin/.gemini/antigravity-ide/brain/5d0a1e09-00a7-4adf-a32e-5186a279bc3c/scratch/map_reduce_output.json", "w") as f:
    json.dump(res, f, indent=2)
print("Done")
