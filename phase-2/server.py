"""
Phase 2 – Backend AI Analysis Server
====================================
Flask server that exposes the review analysis API.
Runs on port 5678 — same port the Phase 1 frontend already calls.

Endpoints:
  GET  /                → health check
  POST /webhook/analyze → analyze a single review text
  POST /webhook/analyze-batch → analyze multiple reviews (for dataset)

Engine priority:
  1. Groq llama-3.3-70b-versatile (if GROQ_API_KEY is configured)
  2. OpenAI gpt-4o-mini  (if OPENAI_API_KEY has credits)
  3. Rule-based VADER    (fallback)
"""

import json
import os
import sys
import time
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Load environment ───────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "phase-6" / "config" / ".env")

# ── Import engines and data strategy ───────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from rule_based_analyzer import RuleBasedAnalyzer
from agents import ReviewAnalysisPipeline
from data_strategy import DataStrategy

# Try to init best available LLM engine:
#   Priority 1: Groq  (free, fast — llama-3.3-70b) ← PRIMARY
#   Priority 2: OpenAI (gpt-4o-mini — fallback)
#   Priority 3: VADER rule-based (always works, no API key)
_pipeline = None
_engine_label = "VADER rule-based (free)"
_openai_available = False

def _try_groq():
    global _pipeline, _engine_label, _openai_available
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key or "your_" in api_key.lower():
        return False
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        # Probe with a real completion to confirm it works
        client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5,
        )
        _pipeline = ReviewAnalysisPipeline(client=client, model="llama-3.1-8b-instant")
        _engine_label = "Groq llama-3.1-8b (free)"
        _openai_available = True
        print("[INFO] Engine: Groq llama-3.3-70b-versatile (FREE) — ACTIVE")
        return True
    except Exception as e:
        print(f"[WARN] Groq unavailable ({type(e).__name__}): {str(e)[:100]}")
        return False

def _try_openai():
    global _pipeline, _engine_label, _openai_available
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or "your_" in api_key.lower():
        return False
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, timeout=15)
        # Probe with a real completion to check quota
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5,
        )
        _pipeline = ReviewAnalysisPipeline(client=client, model="gpt-4o-mini")
        _engine_label = "gpt-4o-mini (OpenAI)"
        _openai_available = True
        print("[INFO] Engine: OpenAI gpt-4o-mini — ACTIVE")
        return True
    except Exception as e:
        msg = str(e)
        if "quota" in msg.lower() or "429" in msg or "insufficient" in msg.lower():
            print("[WARN] OpenAI quota exhausted. Add billing at https://platform.openai.com/account/billing")
        else:
            print(f"[WARN] OpenAI unavailable ({type(e).__name__})")
        return False

# Try engines in priority order
if not _try_groq():
    if not _try_openai():
        print("[INFO] Engine: VADER rule-based (no API key) — ACTIVE")

_rule_engine = RuleBasedAnalyzer()

def get_engine_label():
    return _engine_label

def run_analysis(text: str) -> dict:
    """Run analysis using best available engine."""
    if _pipeline:
        return _pipeline.analyze_review(text)
    return _rule_engine.analyze_review(text)

# ── Flask App Setup ────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

MAX_CHARS = 5000
BASE_DIR = Path(__file__).parent.parent
DATASET_PATH = BASE_DIR / "phase-6" / "storage" / "processed" / "all_reviews.json"


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
def health():
    return jsonify({
        "status": "ok",
        "service": "AI Product Insights Engine – Backend API",
        "version": "3.0.0",
        "engine": get_engine_label(),
        "agents": ["Sentiment", "Pain Point", "User Segment", "Feature Request", "PM Insight (Agent 5)"],
        "openai_active": _openai_available,
        "dataset_available": DATASET_PATH.exists(),
        "dataset_reviews": len(json.load(open(DATASET_PATH, encoding='utf-8'))) if DATASET_PATH.exists() else 0,
        "endpoints": {
            "analyze":         "POST /webhook/analyze",
            "analyze_batch":   "POST /webhook/analyze-batch",
            "analyze_dataset": "POST /webhook/analyze-dataset",
        }
    })


@app.post("/webhook/analyze")
def analyze():
    """
    Analyze a single review text through all 5 agents.
    Body: { "reviews": "<review text>" }
    """
    body = request.get_json(silent=True) or {}
    reviews = body.get("reviews", "")

    # ── Input validation ───────────────────────────────────────────────────────
    if not reviews or not isinstance(reviews, str) or not reviews.strip():
        return jsonify({
            "status": "error",
            "error_code": "EMPTY_INPUT",
            "message": "Input cannot be empty. Please paste some review text."
        }), 400

    trimmed = reviews.strip()
    if len(trimmed) > MAX_CHARS:
        return jsonify({
            "status": "error",
            "error_code": "INPUT_TOO_LONG",
            "message": f"Review text exceeds the {MAX_CHARS:,} character limit.",
            "character_count": len(trimmed),
            "max_allowed": MAX_CHARS,
        }), 400

    # ── Run the analysis (OpenAI or VADER fallback) ────────────────────────────
    try:
        result = run_analysis(trimmed)
        result["meta"] = result.get("meta", {})
        result["meta"]["engine"] = get_engine_label()
        result["meta"]["input_length"] = len(trimmed)
        result["meta"]["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "error_code": "PIPELINE_ERROR",
            "message": f"Analysis pipeline failed: {str(e)}"
        }), 500


@app.post("/webhook/analyze-batch")
def analyze_batch():
    """
    Analyze a batch of reviews from the dataset.
    Body: { "limit": 10 }  (default: 5, max: 20)
    Returns aggregate insights from the sampled reviews.
    """
    body = request.get_json(silent=True) or {}
    limit = min(int(body.get("limit", 5)), 20)

    if not DATASET_PATH.exists():
        return jsonify({
            "status": "error",
            "error_code": "DATASET_NOT_FOUND",
            "message": "Run the Phase 6 scraping pipeline first to generate all_reviews.json"
        }), 404

    with open(DATASET_PATH, encoding="utf-8") as f:
        all_reviews = json.load(f)

    # Prioritize negative reviews (most informative for pain points)
    neg = [r for r in all_reviews if r.get("rating") and r["rating"] <= 2]
    sample = neg[:limit] if len(neg) >= limit else all_reviews[:limit]

    results = []
    for r in sample:
        try:
            analysis = run_analysis(r.get("text", ""))
            analysis["source_review"] = {
                "source": r.get("source"),
                "rating": r.get("rating"),
                "platform": r.get("platform"),
            }
            analysis["meta"] = analysis.get("meta", {})
            analysis["meta"]["engine"] = get_engine_label()
            results.append(analysis)
        except Exception:
            continue

    return jsonify({
        "status": "success",
        "total_analyzed": len(results),
        "dataset_size": len(all_reviews),
        "results": results,
    }), 200


@app.post("/webhook/analyze-dataset")
def analyze_dataset():
    """
    Full dataset PM analysis using the pre-LLM data strategy.
    Uses DataStrategy to filter, sample, and build a context-enriched payload,
    then sends it through the 5-agent pipeline (Groq) for PM-level insights.

    Body (optional): { "sample_size": 250 }
    """
    print(f"DEBUG inside analyze_dataset: _pipeline is {_pipeline}")
    if not _pipeline:
        return jsonify({
            "status": "error",
            "error_code": "NO_LLM_ENGINE",
            "message": f"No LLM engine available. Configure GROQ_API_KEY in phase-6/config/.env. Pipeline object: {_pipeline}"
        }), 503

    if not DATASET_PATH.exists():
        return jsonify({
            "status": "error",
            "error_code": "DATASET_NOT_FOUND",
            "message": "Run the Phase 6 scraping pipeline first to generate all_reviews.json"
        }), 404

    body = request.get_json(silent=True) or {}
    # Allow up to 1000 reviews for chunking (NOTE: this WILL hit Groq rate limits if using free tier)
    sample_size = min(int(body.get("sample_size", 35)), 1000)

    try:
        ds = DataStrategy(dataset_path=DATASET_PATH, sample_size=sample_size)
        
        if sample_size <= 100:
            # Standard single-chunk execution
            payload = ds.prepare()
            result = _pipeline.analyze_dataset(payload)
        else:
            # Map-Reduce Chunking execution
            chunk_payloads = ds.prepare_chunks(chunk_size=100)
            result = _pipeline.analyze_chunked_dataset(chunk_payloads)

        # Inject engine metadata
        if "meta" in result:
            result["meta"]["engine"] = get_engine_label()
            result["meta"]["strategy"] = {
                "noise_filtered": True,
                "stratified_sample": True,
                "context_grounded": True,
                "neg_oversampled": True,
            }

        return jsonify(result), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "error_code": "DATASET_ANALYSIS_ERROR",
            "message": f"Dataset analysis failed: {str(e)}"
        }), 500


# ── Start ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5678))
    print(f"\n{'='*55}")
    print(f"  Phase 2 – AI Product Insights Engine")
    print(f"  Engine: {get_engine_label()}  |  Agents: 5 (4 parallel + PM Insight)")
    print(f"  POST http://localhost:{port}/webhook/analyze")
    print(f"  POST http://localhost:{port}/webhook/analyze-dataset")
    print(f"{'='*55}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
