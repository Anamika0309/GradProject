# Phase 2 – Core AI Workflow (Backend API)

> **Status: IMPLEMENTED ✅**

This phase implements the five-agent AI pipeline inside a backend API server, fully replacing the mock responses from Phase 1. 

- **Agent 1**: Sentiment Agent — classifies Happy / Neutral / Angry
- **Agent 2**: Pain Point Agent — extracts discovery, recommendation, search, and playlist issues
- **Agent 3**: User Segment Agent — detects distinct groups (e.g., Contextual Listeners, Active Explorers)
- **Agent 4**: Feature Request Agent — extracts Needs, Wants, Missing Features
- **Agent 5**: Insight Agent — synthesizes all outputs into the robust PM Product Insights Engine JSON schema.

## Architecture

We moved away from the original n8n design to a robust Python-based API server. 

```
phase-2/
  agents.py                # AI pipeline orchestrator handling the 5 parallel agents
  server.py                # Flask API server handling frontend requests
  data_strategy.py         # Pre-LLM data pipeline for large datasets (Phase 6 integration)
  rule_based_analyzer.py   # Fallback VADER analysis engine
  requirements.txt         # Python dependencies
  docs/
    README.md              # This file
```

## Prerequisites
- Phase 1 frontend complete
- `GROQ_API_KEY` (primary) or `OPENAI_API_KEY` (fallback) configured in `phase-6/config/.env`

## How to Run
1. Install dependencies: `pip install -r phase-2/requirements.txt`
2. Start the backend server: `python phase-2/server.py`
3. The server runs on `http://localhost:5678` (the exact same port as the Phase 1 mock backend).
4. Send a POST request to `/webhook/analyze` with `{"reviews": "<review text>"}` or simply use the Phase 1 frontend UI, which will automatically talk to this new AI server!
