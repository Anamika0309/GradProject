"""
Phase 2 – AI Multi-Agent Workflow
==================================
Five-agent system for analyzing Spotify reviews:

  Agent 1 – Sentiment Agent       → classifies emotional tone
  Agent 2 – Pain Point Agent      → extracts specific issues
  Agent 3 – User Segment Agent    → identifies user types
  Agent 4 – Feature Request Agent → captures feature needs
  Agent 5 – Insight Agent         → synthesizes all findings

Agents 1–4 run IN PARALLEL via ThreadPoolExecutor.
Agent 5 receives all four outputs and synthesizes the final result.

Supported LLM providers (in priority order):
  1. Groq  (free tier: llama-3.3-70b-versatile) — recommended
  2. OpenAI (gpt-4o-mini)                         — if OPENAI_API_KEY has credits
"""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "phase-6" / "config" / ".env")

# ── Configuration ────────────────────────────────────────────────────────────

@dataclass
class AgentConfig:
    model: str = "llama-3.3-70b-versatile"  # Groq default (free)
    temperature: float = 0.3
    max_tokens: int = 800
    timeout_seconds: int = 30

AGENT_TIMEOUT = 30
INSIGHT_TIMEOUT = 45


# ── Core Agent Caller ────────────────────────────────────────────────────────────

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(4),
    retry=retry_if_exception_type(Exception)
)
def _call_llm_with_retry(client, config: AgentConfig, system_prompt: str, user_input: str) -> dict:
    """Internal function to call LLM with tenacity retry for rate limits/transient errors."""
    response = client.chat.completions.create(
        model=config.model,
        messages=[
            {
                "role": "system",
                "content": system_prompt + "\n\nIMPORTANT: Return ONLY valid JSON. No markdown, no text outside the JSON object."
            },
            {"role": "user", "content": user_input}
        ],
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    return json.loads(raw)


def _call_llm(client, config: AgentConfig, system_prompt: str, user_input: str) -> dict:
    """Call LLM (Groq or OpenAI) with JSON mode and automatic retries. Returns parsed dict or error dict."""
    try:
        return _call_llm_with_retry(client, config, system_prompt, user_input)
    except Exception as e:
        print(f"[LLM Error] {type(e).__name__}: {str(e)[:200]}")
        return {"_error": str(e)}


# ── Agent 1: Sentiment ─────────────────────────────────────────────────────────

def agent_sentiment(client, config: AgentConfig, review_text: str) -> Dict[str, Any]:
    """Classify emotional tone of the review."""
    prompt = """You are a sentiment analysis expert for app reviews.
Analyze the emotional tone of this Spotify review.
Return exactly this JSON structure:
{
  "overall": "Happy" | "Neutral" | "Angry",
  "confidence": <float 0.0-1.0>,
  "key_emotions": ["<emotion1>", "<emotion2>"],
  "summary": "<1-2 sentences explaining the sentiment>"
}"""
    result = _call_llm(client, config, prompt, review_text)
    if "_error" in result:
        return {"overall": "Neutral", "confidence": 0.5, "key_emotions": [], "summary": "Analysis unavailable."}
    return result


# ── Agent 2: Pain Points ───────────────────────────────────────────────────────

def agent_pain_points(client, config: AgentConfig, review_text: str) -> Dict[str, Any]:
    """Extract specific pain points from the review."""
    prompt = """You are a product analyst for Spotify. Extract pain points from this user review.
Focus on music discovery, recommendations, search, playlists, and technical issues.
Return exactly this JSON structure:
{
  "discovery_issues": ["<issue1>", "<issue2>"],
  "recommendation_issues": ["<issue1>", "<issue2>"],
  "search_issues": ["<issue1>"],
  "playlist_issues": ["<issue1>"],
  "technical_issues": ["<issue1>"],
  "other_issues": ["<issue1>"]
}
Only include issues explicitly mentioned. Empty arrays if none."""
    result = _call_llm(client, config, prompt, review_text)
    if "_error" in result:
        return {"discovery_issues": [], "recommendation_issues": [], "search_issues": [], "playlist_issues": [], "technical_issues": [], "other_issues": []}
    return result


# ── Agent 3: User Segment ──────────────────────────────────────────────────────

def agent_user_segment(client, config: AgentConfig, review_text: str) -> Dict[str, Any]:
    """Identify the user type from contextual clues."""
    prompt = """You are a user research analyst. Identify the user segment from this Spotify review.
Look for context clues about lifestyle, usage patterns, and music preferences.
Return exactly this JSON structure:
{
  "primary_segment": "Student" | "Gym User" | "Parent" | "Casual" | "Audiophile" | "Commuter" | "Professional" | "Unknown",
  "confidence": <float 0.0-1.0>,
  "evidence": ["<phrase from review that supports this>"],
  "secondary_segments": ["<segment1>"]
}"""
    result = _call_llm(client, config, prompt, review_text)
    if "_error" in result:
        return {"primary_segment": "Unknown", "confidence": 0.3, "evidence": [], "secondary_segments": []}
    return result


# ── Agent 4: Feature Requests ──────────────────────────────────────────────────

def agent_feature_requests(client, config: AgentConfig, review_text: str) -> Dict[str, Any]:
    """Capture feature requests and desired improvements."""
    prompt = """You are a product manager for Spotify. Extract feature requests from this user review.
Return exactly this JSON structure:
{
  "critical_needs": ["<must-have feature user demands>"],
  "nice_to_haves": ["<would-be-nice feature>"],
  "missing_features": ["<feature that doesn't exist yet>"],
  "improvements": ["<existing feature that needs improving>"]
}
Only extract features explicitly mentioned. Empty arrays if none."""
    result = _call_llm(client, config, prompt, review_text)
    if "_error" in result:
        return {"critical_needs": [], "nice_to_haves": [], "missing_features": [], "improvements": []}
    return result


def agent_insight(client, config: AgentConfig, review_text: str, agent_outputs: dict) -> Dict[str, Any]:
    """Synthesize all four agent outputs into final structured insights."""
    prompt = """You are a Senior Product Manager and Product Research Analyst at Spotify. 
You have received analysis from 4 specialized AI agents regarding a set of user reviews.
Your goal is NOT just to summarize, but to synthesize evidence, identify patterns, infer user motivations, explain root causes, and generate actionable product insights.

For this dataset, perform these steps internally:
1. Extract facts from reviews.
2. Cluster similar complaints.
3. Identify recurring themes.
4. Infer user goals and motivations.
5. Identify underlying root causes instead of surface complaints.
6. Identify unmet user needs.
7. Identify distinct user segments based on behavior.
8. Generate strategic product insights.
9. Generate AI product opportunities.

Return exactly this JSON structure (and ONLY valid JSON):
{
  "executive_summary": {
    "overall_problem": "<string>",
    "primary_user_need": "<string>",
    "biggest_opportunity": "<string>"
  },
  "sentiment_analysis": {
    "overall_sentiment": "<string>",
    "confidence": "<string>",
    "distribution": {"Positive": "<string>", "Neutral": "<string>", "Negative": "<string>"}
  },
  "key_pain_points": [
    {"pain_point": "<string>", "frequency": "<string>", "severity": "<string>", "example_reviews": ["<string>"]}
  ],
  "root_causes": [
    {"problem": "<string>", "reasoning": "<string>", "supporting_evidence": ["<string>"]}
  ],
  "recommendation_frustrations": [
    {"issue": "<string>", "why_it_happens": "<string>"}
  ],
  "desired_listening_behaviors": [
    {"behavior": "<string>", "user_goal": "<string>"}
  ],
  "repeat_listening_causes": [
    {"cause": "<string>", "evidence": "<string>"}
  ],
  "user_segments": [
    {"segment": "<string>", "description": "<string>", "discovery_challenges": ["<string>"], "needs": ["<string>"]}
  ],
  "unmet_needs": [
    {"need": "<string>", "importance": "<string>", "supporting_reviews": ["<string>"]}
  ],
  "feature_requests": [
    {"feature": "<string>", "reason": "<string>"}
  ],
  "strategic_product_insights": [
    {"insight": "<string>", "business_impact": "<string>", "user_impact": "<string>"}
  ],
  "ai_product_opportunities": [
    {"opportunity": "<string>", "why_ai_is_needed": "<string>", "expected_user_value": "<string>"}
  ],
  "confidence_assessment": {
    "high_confidence_findings": ["<string>"],
    "medium_confidence_findings": ["<string>"],
    "low_confidence_findings": ["<string>"]
  }
}
Do not hallucinate. Every insight must be supported by the provided data.
"""

    context = (
        f"Original Review(s):\n{review_text}\n\n"
        f"Agent Outputs:\n{json.dumps(agent_outputs, indent=2)}"
    )
    # Insight agent gets more tokens since it synthesizes everything
    insight_config = AgentConfig(
        model=config.model,
        temperature=config.temperature,
        max_tokens=2500, # Increased for detailed PM JSON
        timeout_seconds=INSIGHT_TIMEOUT,
    )
    result = _call_llm(client, insight_config, prompt, context)
    if "_error" in result:
        return {"_error": result["_error"]}
    return result


def agent_master_synthesizer(client, config: AgentConfig, chunk_results: list) -> Dict[str, Any]:
    """Reduce/synthesize multiple chunk results into a final master report."""
    prompt = """You are the Lead Product Insights Director at Spotify.
You have received several individual chunk-level analysis reports generated from thousands of user reviews.
Your goal is to perform a Map-Reduce operation: merge, deduplicate, and synthesize these separate chunk reports into ONE master PM Insight JSON report.

Do not drop critical evidence, but group similar pain points and feature requests across chunks.
Recalculate the overall sentiment distribution based on the aggregate data.

Return exactly this JSON structure (and ONLY valid JSON):
{
  "executive_summary": {
    "overall_problem": "<string>",
    "primary_user_need": "<string>",
    "biggest_opportunity": "<string>"
  },
  "sentiment_analysis": {
    "overall_sentiment": "<string>",
    "confidence": "<string>",
    "distribution": {"Positive": "<string>", "Neutral": "<string>", "Negative": "<string>"}
  },
  "key_pain_points": [
    {"pain_point": "<string>", "frequency": "<string>", "severity": "<string>", "example_reviews": ["<string>"]}
  ],
  "root_causes": [
    {"problem": "<string>", "reasoning": "<string>", "supporting_evidence": ["<string>"]}
  ],
  "recommendation_frustrations": [
    {"issue": "<string>", "why_it_happens": "<string>"}
  ],
  "desired_listening_behaviors": [
    {"behavior": "<string>", "user_goal": "<string>"}
  ],
  "repeat_listening_causes": [
    {"cause": "<string>", "evidence": "<string>"}
  ],
  "user_segments": [
    {"segment": "<string>", "description": "<string>", "discovery_challenges": ["<string>"], "needs": ["<string>"]}
  ],
  "unmet_needs": [
    {"need": "<string>", "importance": "<string>", "supporting_reviews": ["<string>"]}
  ],
  "feature_requests": [
    {"feature": "<string>", "reason": "<string>"}
  ],
  "strategic_product_insights": [
    {"insight": "<string>", "business_impact": "<string>", "user_impact": "<string>"}
  ],
  "ai_product_opportunities": [
    {"opportunity": "<string>", "why_ai_is_needed": "<string>", "expected_user_value": "<string>"}
  ],
  "confidence_assessment": {
    "high_confidence_findings": ["<string>"],
    "medium_confidence_findings": ["<string>"],
    "low_confidence_findings": ["<string>"]
  }
}
"""
    # Build context from chunks
    context_parts = []
    for i, res in enumerate(chunk_results):
        context_parts.append(f"--- Chunk {i+1} ---\n{json.dumps(res, indent=2)}")
    context = "\n\n".join(context_parts)

    insight_config = AgentConfig(
        model=config.model,
        temperature=config.temperature,
        max_tokens=4000, 
        timeout_seconds=INSIGHT_TIMEOUT,
    )
    
    print("  🧠 Master Agent Synthesizing across all chunks...")
    result = _call_llm(client, insight_config, prompt, context)
    if "_error" in result:
        return {"_error": result["_error"]}
    return result


# ── Main Pipeline ────────────────────────────────────────────────────────────

class ReviewAnalysisPipeline:
    """
    Orchestrates all 5 agents.
    Agents 1-4 execute IN PARALLEL, Agent 5 synthesizes their outputs.
    Works with both Groq and OpenAI clients (identical API interface).
    """

    def __init__(self, client=None, model: str = "llama-3.3-70b-versatile"):
        """
        client: a Groq or OpenAI client instance
        model:  model name for the chosen provider
        """
        self.client = client
        self.config = AgentConfig(model=model)

    def analyze_review(self, review_text: str) -> Dict[str, Any]:
        """
        Run all 5 agents on a single review.
        Agents 1-4 run in parallel threads, Agent 5 receives all outputs.
        """
        start = time.time()

        # ── Step 1: Run agents 1-4 IN PARALLEL ────────────────────────────────
        parallel_agents = {
            "sentiment":        lambda: agent_sentiment(self.client, self.config, review_text),
            "pain_points":      lambda: agent_pain_points(self.client, self.config, review_text),
            "user_segment":     lambda: agent_user_segment(self.client, self.config, review_text),
            "feature_requests": lambda: agent_feature_requests(self.client, self.config, review_text),
        }

        agent_results = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {name: executor.submit(fn) for name, fn in parallel_agents.items()}
            for name, future in futures.items():
                try:
                    agent_results[name] = future.result(timeout=AGENT_TIMEOUT)
                except FuturesTimeout:
                    agent_results[name] = {"_error": "timeout"}
                except Exception as e:
                    agent_results[name] = {"_error": str(e)}

        # ── Step 2: Agent 5 synthesizes all outputs ────────────────────────────
        insights = agent_insight(self.client, self.config, review_text, agent_results)

        elapsed = round(time.time() - start, 2)

        return {
            "status": "success",
            "executive_summary": insights.get("executive_summary", {}),
            "sentiment_analysis": insights.get("sentiment_analysis", {}),
            "key_pain_points": insights.get("key_pain_points", []),
            "root_causes": insights.get("root_causes", []),
            "recommendation_frustrations": insights.get("recommendation_frustrations", []),
            "desired_listening_behaviors": insights.get("desired_listening_behaviors", []),
            "repeat_listening_causes": insights.get("repeat_listening_causes", []),
            "user_segments": insights.get("user_segments", []),
            "unmet_needs": insights.get("unmet_needs", []),
            "feature_requests": insights.get("feature_requests", []),
            "strategic_product_insights": insights.get("strategic_product_insights", []),
            "ai_product_opportunities": insights.get("ai_product_opportunities", []),
            "confidence_assessment": insights.get("confidence_assessment", {}),
            "meta": {
                "model": self.config.model,
                "agents_used": 5,
                "parallel_agents": 4,
                "elapsed_seconds": elapsed,
            }
        }

    def analyze_dataset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a full dataset using the pre-processed DataStrategy payload.

        Unlike analyze_review (single review → 5 agents), this method:
          - Runs Agents 1-4 on the full sampled review text
          - Passes both the agent outputs AND the context summary to Agent 5
          - Agent 5 reasons across all reviews like a PM, not a summarizer

        Args:
            payload: Dict from DataStrategy.prepare() containing:
              - sample_text:      concatenated context + reviews
              - context_summary:  pre-computed dataset statistics
              - sample_reviews:   list of raw review dicts
              - estimated_tokens: token estimate
              - reviews_included: number of reviews in the payload
        """
        start = time.time()
        sample_text = payload["sample_text"]
        context_summary = payload["context_summary"]

        print(f"[Pipeline] analyze_dataset: {payload['reviews_included']} reviews, ~{payload['estimated_tokens']:,} tokens")

        # ── Step 1: Run agents 1-4 IN PARALLEL on the full sample text ─────────
        # Use a higher token budget since we're analyzing many reviews at once
        dataset_config = AgentConfig(
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=1500,  # More headroom for multi-review extraction
            timeout_seconds=60,
        )

        parallel_agents = {
            "sentiment":        lambda: agent_sentiment(self.client, dataset_config, sample_text),
            "pain_points":      lambda: agent_pain_points(self.client, dataset_config, sample_text),
            "user_segment":     lambda: agent_user_segment(self.client, dataset_config, sample_text),
            "feature_requests": lambda: agent_feature_requests(self.client, dataset_config, sample_text),
        }

        agent_results = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {name: executor.submit(fn) for name, fn in parallel_agents.items()}
            for name, future in futures.items():
                try:
                    agent_results[name] = future.result(timeout=60)
                    print(f"  ✅ Agent {name} completed")
                except FuturesTimeout:
                    agent_results[name] = {"_error": "timeout"}
                    print(f"  ⏱️ Agent {name} timed out")
                except Exception as e:
                    agent_results[name] = {"_error": str(e)}
                    print(f"  ❌ Agent {name} failed: {e}")

        # ── Step 2: Agent 5 with context grounding ─────────────────────────────
        # Inject the statistical context so Agent 5 knows the full dataset shape
        enriched_context = (
            f"Original Review(s):\n{sample_text}\n\n"
            f"Agent Outputs:\n{json.dumps(agent_results, indent=2)}\n\n"
            f"=== FULL DATASET STATISTICS (for grounding) ===\n"
            f"{json.dumps(context_summary, indent=2)}\n"
            f"=== END STATISTICS ===\n"
        )

        insight_config = AgentConfig(
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=3500,  # Large output for detailed PM analysis
            timeout_seconds=90,
        )

        # Call Agent 5 directly (not through agent_insight to pass custom context)
        prompt = """You are a Senior Product Manager and Product Research Analyst at Spotify.
You have received analysis from 4 specialized AI agents AND full dataset statistics.

Your goal is NOT to summarize. Your goal is to SYNTHESIZE evidence across ALL reviews,
identify patterns, infer user motivations, explain root causes, and generate actionable product insights.

The "FULL DATASET STATISTICS" section shows you data from the ENTIRE dataset of thousands of reviews,
even though you only read a sample. Use these statistics to calibrate your confidence levels.

For this dataset, perform these steps internally:
1. Extract facts from reviews.
2. Cluster similar complaints.
3. Identify recurring themes.
4. Infer user goals and motivations.
5. Identify underlying root causes instead of surface complaints.
6. Identify unmet user needs.
7. Identify distinct user segments based on behavior (NOT demographics).
8. Generate strategic product insights.
9. Generate AI product opportunities.

Return exactly this JSON structure (and ONLY valid JSON):
{
  "executive_summary": {
    "overall_problem": "<string>",
    "primary_user_need": "<string>",
    "biggest_opportunity": "<string>"
  },
  "sentiment_analysis": {
    "overall_sentiment": "<string>",
    "confidence": "<string>",
    "distribution": {"Positive": "<string>", "Neutral": "<string>", "Negative": "<string>"}
  },
  "key_pain_points": [
    {"pain_point": "<string>", "frequency": "<string>", "severity": "<string>", "example_reviews": ["<string>"]}
  ],
  "root_causes": [
    {"problem": "<string>", "reasoning": "<string>", "supporting_evidence": ["<string>"]}
  ],
  "recommendation_frustrations": [
    {"issue": "<string>", "why_it_happens": "<string>"}
  ],
  "desired_listening_behaviors": [
    {"behavior": "<string>", "user_goal": "<string>"}
  ],
  "repeat_listening_causes": [
    {"cause": "<string>", "evidence": "<string>"}
  ],
  "user_segments": [
    {"segment": "<string>", "description": "<string>", "discovery_challenges": ["<string>"], "needs": ["<string>"]}
  ],
  "unmet_needs": [
    {"need": "<string>", "importance": "<string>", "supporting_reviews": ["<string>"]}
  ],
  "feature_requests": [
    {"feature": "<string>", "reason": "<string>"}
  ],
  "strategic_product_insights": [
    {"insight": "<string>", "business_impact": "<string>", "user_impact": "<string>"}
  ],
  "ai_product_opportunities": [
    {"opportunity": "<string>", "why_ai_is_needed": "<string>", "expected_user_value": "<string>"}
  ],
  "confidence_assessment": {
    "high_confidence_findings": ["<string>"],
    "medium_confidence_findings": ["<string>"],
    "low_confidence_findings": ["<string>"]
  }
}

IMPORTANT RULES:
- Generate 3-5 items per list. Be specific, not generic.
- Every insight MUST be supported by evidence from the reviews.
- Use the dataset statistics to calibrate confidence levels.
- Do NOT hallucinate. If evidence is thin, say so.
"""

        print("  🧠 Agent 5 (PM Insight Engine) synthesizing...")
        result = _call_llm(self.client, insight_config, prompt, enriched_context)

        elapsed = round(time.time() - start, 2)

        if "_error" in result:
            return {
                "status": "error",
                "message": f"Insight agent failed: {result['_error']}",
                "meta": {"elapsed_seconds": elapsed},
            }

        # Build the final response
        response = {
            "status": "success",
            "executive_summary": result.get("executive_summary", {}),
            "sentiment_analysis": result.get("sentiment_analysis", {}),
            "key_pain_points": result.get("key_pain_points", []),
            "root_causes": result.get("root_causes", []),
            "recommendation_frustrations": result.get("recommendation_frustrations", []),
            "desired_listening_behaviors": result.get("desired_listening_behaviors", []),
            "repeat_listening_causes": result.get("repeat_listening_causes", []),
            "user_segments": result.get("user_segments", []),
            "unmet_needs": result.get("unmet_needs", []),
            "feature_requests": result.get("feature_requests", []),
            "strategic_product_insights": result.get("strategic_product_insights", []),
            "ai_product_opportunities": result.get("ai_product_opportunities", []),
            "confidence_assessment": result.get("confidence_assessment", {}),
            "meta": {
                "model": self.config.model,
                "mode": "dataset",
                "agents_used": 5,
                "parallel_agents": 4,
                "reviews_analyzed": payload["reviews_included"],
                "dataset_total": context_summary.get("total_reviews_in_dataset", 0),
                "estimated_tokens": payload["estimated_tokens"],
                "elapsed_seconds": elapsed,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        }

        print(f"  ✅ Dataset analysis complete in {elapsed}s")
        return response

    def analyze_chunked_dataset(self, payloads: list) -> Dict[str, Any]:
        """
        Analyze a dataset > 100 reviews by processing it in chunks and map-reducing.
        """
        start = time.time()
        print(f"[Pipeline] Map-Reduce started for {len(payloads)} chunks.")
        
        chunk_results = []
        total_reviews = 0
        total_estimated_tokens = 0
        
        for i, payload in enumerate(payloads):
            print(f"\n[Chunk {i+1}/{len(payloads)}] Processing...")
            result = self.analyze_dataset(payload)
            if result.get("status") == "success":
                # Only keep the insights, discard meta for the master synthesis
                clean_result = {k: v for k, v in result.items() if k not in ("status", "meta")}
                chunk_results.append(clean_result)
                total_reviews += payload.get("reviews_included", 0)
                total_estimated_tokens += payload.get("estimated_tokens", 0)
            else:
                print(f"  ❌ Chunk {i+1} failed: {result.get('message')}")
                
            # If not the last chunk, pause to respect Groq TPM sliding window limits
            if i < len(payloads) - 1:
                print(f"  ⏳ Pausing 45s before next chunk to respect TPM limits...")
                time.sleep(45)
                
        if not chunk_results:
            return {"status": "error", "message": "All chunks failed to process."}
            
        print("\n[Pipeline] Map phase complete. Starting Reduce phase...")
        final_result = agent_master_synthesizer(self.client, self.config, chunk_results)
        
        elapsed = round(time.time() - start, 2)
        if "_error" in final_result:
            return {
                "status": "error",
                "message": f"Master synthesis failed: {final_result['_error']}",
                "meta": {"elapsed_seconds": elapsed},
            }
            
        # Build final response
        response = {
            "status": "success",
            **final_result,
            "meta": {
                "model": self.config.model,
                "mode": "map_reduce_chunked",
                "agents_used": 6, # 4 parallel + 1 insight (per chunk) + 1 master
                "chunks_processed": len(chunk_results),
                "reviews_analyzed": total_reviews,
                "estimated_tokens": total_estimated_tokens,
                "elapsed_seconds": elapsed,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        }
        print(f"✅ Map-Reduce chunking complete in {elapsed}s")
        return response


# ── CLI Test ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    groq_key = os.getenv("GROQ_API_KEY", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")

    if groq_key and "your_" not in groq_key.lower():
        from groq import Groq
        client = Groq(api_key=groq_key)
        model = "llama-3.3-70b-versatile"
        print("Using: Groq llama-3.3-70b-versatile (free)")
    elif openai_key and "your_" not in openai_key.lower():
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        model = "gpt-4o-mini"
        print("Using: OpenAI gpt-4o-mini")
    else:
        print("ERROR: Set GROQ_API_KEY or OPENAI_API_KEY in phase-6/config/.env")
        sys.exit(1)

    pipeline = ReviewAnalysisPipeline(client=client, model=model)

    # Test mode: single review
    sample = (
        "I've been using Spotify for 3 years and the Discover Weekly has gotten so repetitive. "
        "It keeps recommending the same 10 artists every week. I'm a college student trying to "
        "find new music for studying but the algorithm seems broken. The search function is also "
        "terrible — it never shows me the songs I actually want. Please fix the recommendation engine!"
    )

    print("Running 5-agent parallel pipeline...")
    result = pipeline.analyze_review(sample)
    print(json.dumps(result, indent=2, ensure_ascii=False))

