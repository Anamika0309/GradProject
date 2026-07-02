# Problem Statement: AI-Powered Review Discovery Engine

## Context

You are a Product Manager on the Growth Team at **Spotify**.

The company has successfully acquired millions of users and built one of the world's most sophisticated recommendation systems. However, a significant percentage of listening still comes from repeat playlists, familiar artists, and previously discovered tracks.

One of Spotify's strategic goals is to **increase meaningful music discovery** and **reduce repetitive listening behavior**.

To inform product decisions, the team needs a scalable way to understand what users are saying across public feedback channels — not just in aggregate ratings, but in the language, patterns, and pain points embedded in reviews and community discussions.

---

## Objective

Build an **AI-Powered Review Discovery Engine** that analyzes user feedback at scale and surfaces actionable product insights related to music discovery and listening behavior.

The system must be **publicly accessible** so that senior reviewers can upload a link, paste sample reviews, and verify that the workflow runs end-to-end without requiring local setup, credentials, or a walkthrough demo.

---

## Recommended Architecture

Use a **multi-agent pipeline** instead of a single monolithic GPT prompt. Each agent has a focused responsibility; a final Insight Agent synthesizes their outputs into the report returned to the frontend.

```
Simple Web Page (Frontend)
        │
        ▼
Backend API Endpoint
        │
        ▼
┌───────────────────────────────────────────────────┐
│  Parallel Agent Analysis (GPT / Claude)           │
│                                                   │
│  Agent 1: Sentiment    Agent 2: Pain Point        │
│  Agent 3: User Segment Agent 4: Feature Request   │
└───────────────────────────────────────────────────┘
        │
        ▼
Agent 5: Insight Agent (synthesizes all agent outputs)
        │
        ▼
Structured Analysis (JSON)
        │
        ▼
Results displayed on Frontend
```

### AI Agents

53:Each agent is implemented as a dedicated LLM step inside the backend API workflow, with its own focused prompt and output schema.

#### Agent 1 — Sentiment Agent

Classify overall sentiment across the pasted reviews.

| Output | Description |
|---|---|
| Happy | Positive reviews and satisfaction signals |
| Neutral | Mixed or indifferent feedback |
| Angry | Negative reviews and strong dissatisfaction |

#### Agent 2 — Pain Point Agent

Extract and categorize user pain points related to music discovery and listening.

| Category | Description |
|---|---|
| Recommendation issue | Problems with suggested music, repetition, or irrelevant picks |
| Search issue | Difficulty finding specific songs, artists, or genres |
| Playlist issue | Frustrations with playlists, curation, or organization |
| Discovery issue | Struggles discovering new music or breaking out of familiar listening |

#### Agent 3 — User Segment Agent

Predict which user segments are represented in the review text.

| Segment | Description |
|---|---|
| Student | Study, focus, budget-conscious, or campus listening patterns |
| Gym User | Workout, high-energy, playlist-driven listening |
| Parent | Family accounts, kid-friendly content, shared listening |
| Casual Listener | Background listening, low engagement with discovery features |
| Audiophile | Sound quality, catalog depth, and advanced feature expectations |

#### Agent 4 — Feature Request Agent

Extract explicit and implied product asks from the reviews.

| Category | Description |
|---|---|
| Needs | Core gaps users require the product to address |
| Wants | Desired improvements that are not strictly blockers |
| Missing features | Functionality users expect but cannot find |

#### Agent 5 — Insight Agent

Reads the structured outputs from Agents 1–4 and produces the **final report** returned to the frontend.

Responsibilities:

- Synthesize cross-agent findings into a coherent narrative
- Map agent outputs to the six frontend Results sections
- Surface **Recommended Product Opportunities** backed by evidence from the other agents
- Return a single **fixed JSON schema** the frontend can render reliably

**Orchestration in the backend API:** Agents 1–4 may run in parallel after the API receives review text; Agent 5 runs after all four complete and aggregates their outputs before the API responds.

### Backend API Workflow

- Implement the analysis pipeline as a backend API workflow triggered by a **POST** endpoint.
- The endpoint accepts pasted review text (and optionally metadata such as source or date).
- The backend orchestrates **five AI agents** (Sentiment, Pain Point, User Segment, Feature Request, Insight) rather than a single catch-all prompt.
- Agents 1–4 each call **GPT or Claude** with a focused prompt and return structured output for their domain.
- Agent 5 reads all prior agent outputs and produces the final report using a **fixed JSON schema** so the frontend does not break on malformed responses.
- The backend returns a **structured JSON** response to the frontend.
- The endpoint returns **clear error messages** for failure cases (e.g., empty input, timeout, LLM failure).
- **CORS** must be configured so the API accepts requests from the deployed frontend origin.
- Enforce **input limits** (character or review count cap) in the backend to control LLM cost and latency during the public demo.

### Frontend: Minimal Single-Page App

Keep the frontend intentionally minimal — no login, no fancy design. Just enough for a reviewer to test the workflow.

**Page title:** Spotify Review Analyzer

**Layout:**

```
Spotify Review Analyzer

------------------------

Paste Reviews

[Text Area]

[Load sample reviews]  [Analyze Reviews]

------------------------

Results

- Pain Points
- Top Complaints
- User Segments
- Feature Requests
- Unmet Needs
- Recommended Product Opportunities

(Loading indicator shown while analysis runs)
```

**Behavior:**

1. User pastes review text into the text area (or clicks **Load sample reviews** to populate the text area instantly).
2. User clicks **Analyze Reviews**.
3. Frontend validates input length before sending; show a clear message if the limit is exceeded.
4. Frontend shows a **loading state** while the API/LLM runs (analysis may take several seconds).
5. Frontend sends the text to the backend API endpoint.
6. Frontend displays the returned insights in the Results section, or a clear error message if the request fails.

---

## Review Data Sources

The engine should be designed to analyze feedback from sources such as:

- App Store reviews
- Play Store reviews
- Reddit discussions
- Community forums
- Social media conversations

For the initial build, pasted text in the frontend is sufficient. The architecture should remain extensible so additional ingestion steps (CSV upload, API pulls, scheduled scraping) can be added to the backend workflow later.

---

## Analysis Questions the Engine Must Answer

The AI review engine must help answer the following questions (and **similar, closely related questions** on the same themes):

1. **Why do users struggle to discover new music?**
2. **What are the most common frustrations with recommendations?**
3. **What listening behaviors are users trying to achieve?**
4. **What causes users to repeatedly listen to the same content?**
5. **Which user segments experience different discovery challenges?**
6. **What unmet needs emerge consistently across reviews?**

The structured JSON output (produced by Agent 5) should map directly to the frontend Results sections:

| Result Section | Primary Agent(s) | Analysis Focus |
|---|---|---|
| Pain Points | Agent 2 (Pain Point) | Recurring friction and blockers in the discovery experience |
| Top Complaints | Agent 1 (Sentiment) + Agent 2 (Pain Point) | Most frequently cited negative themes and angry/neutral signals |
| User Segments | Agent 3 (User Segment) | Distinct groups with different discovery challenges |
| Feature Requests | Agent 4 (Feature Request) | Explicit or implied product asks from users |
| Unmet Needs | Agent 4 (Feature Request) | Core needs and gaps between user expectations and current experience |
| Recommended Product Opportunities | Agent 5 (Insight) | Actionable growth or product bets backed by evidence from all agents |

---

## Technology Stack

You may use any AI-native stack. The recommended approach for this project is:

| Layer | Technology |
|---|---|
| Workflow orchestration | **Backend API** (POST endpoint) |
| AI analysis | **Multi-agent pipeline** — five focused agents orchestrated in the backend |
| LLM provider | **GPT** or **Claude** (one call per agent) |
| Frontend | Minimal single-page app (e.g., HTML/JS or lightweight React) |
| Frontend hosting | **Vercel** (or equivalent static/hosted frontend) |
| Backend hosting | Public host, server, or cloud service |

218:The core deliverable is a backend API workflow where specialized agents analyze reviews in parallel and an Insight Agent returns structured JSON to the frontend. Other tools (RAG systems, Zapier, Perplexity, etc.) may be added later if they add clear value.

---

## Implementation Roadmap

1. **Collect review data** — Gather representative App Store, Play Store, Reddit, and forum reviews related to Spotify music discovery and recommendations. Use these as test inputs and for the **Load sample reviews** button.
2. **Build the backend API** — Create a POST endpoint that receives review text, enforces **input limits**, configures **CORS**, and orchestrates the five-agent pipeline.
3. **Implement AI agents** — Build Agents 1–4 (Sentiment, Pain Point, User Segment, Feature Request) with focused prompts; run them in parallel where possible. Build Agent 5 (Insight) to synthesize their outputs into a **fixed JSON schema** aligned with the frontend Results sections.
4. **Return structured JSON with error handling** — Ensure Agent 5's final report maps cleanly to the frontend Results UI; return clear error messages for empty input, timeouts, and LLM failures.
5. **Build the frontend** — One page with text area, **Load sample reviews** and **Analyze Reviews** buttons, **loading state**, input validation, and Results display.
6. **Deploy the frontend** — e.g., on Vercel.
7. **Deploy the backend API** — e.g., on a public host or managed cloud service.
8. **Connect frontend and backend API** — Wire the frontend to the public API endpoint; verify **CORS** from the deployed origin.
9. **Verify the public link** — Confirm seniors can open the link, load or paste reviews, and receive analysis (or clear errors) without any local setup.

---

## Deliverables

1. **Public demo link** — A live URL where senior reviewers can paste reviews and test the workflow end-to-end.
2. **Backend API workflow** — Documented setup showing POST endpoint → five AI agents → Insight Agent → structured JSON.
3. **Frontend source** — Minimal single-page app connected to the webhook.
4. **Sample test data** — A small set of representative reviews used to validate output quality during demo.

---

## Success Criteria

- A senior reviewer can open the public link, paste reviews (or load sample reviews), click **Analyze Reviews**, and see structured results within a reasonable response time.
- Output addresses the six core analysis questions and supports similar follow-up questions on the same themes.
- All five agents run successfully within the backend workflow; Agent 5 returns a synthesized report as structured JSON (fixed schema) rendered in all six Results sections.
- No login or local environment is required to test the workflow.
- The system demonstrates a clear path from raw user feedback to actionable product insights for Spotify's discovery and growth goals.
- Errors (empty input, timeout, LLM failure, over-limit input) surface as clear user-facing messages — not a blank screen.
- A loading indicator is visible while analysis is in progress.
- CORS and input limits are configured and working in the deployed environment.

---

## Implementation Requirements

The following are **in scope** for the initial build:

1. **Fixed JSON schema** — Agent 5 (Insight Agent) must output a fixed JSON schema so the final report is predictable and the frontend does not break on malformed responses. Agents 1–4 should also return structured output Agent 5 can consume reliably.
2. **Error handling** — Return clear error messages from the webhook (e.g., empty input, timeout, LLM failure) so reviewers see useful feedback instead of a blank screen.
3. **Input limits** — Cap pasted text length (character or review count) on both frontend and backend workflow to control LLM cost and latency during the public demo (five agent calls per request).
4. **CORS configuration** — Ensure the backend API allows requests from the deployed frontend origin.
5. **Sample reviews** — Provide a **Load sample reviews** button on the frontend so reviewers can test instantly without sourcing their own data.
6. **Loading state** — Show a simple loading indicator while the webhook/LLM runs; analysis may take several seconds.

### Out of Scope (for now)

The following are deferred and **not required** for the initial build:

- **Prompt versioning** — Formal traceability of prompt iterations during review.
- **Future ingest extension** — Separate backend ingest branch for CSV upload, scheduled Reddit pulls, or App Store API integration.
