# Detailed Architecture for AI-Powered Review Discovery Engine

## 1. System Overview

The AI-Powered Review Discovery Engine is a public-facing product analytics system that helps reviewers and product teams understand user feedback about music discovery and listening behavior. The system accepts user-submitted review text or scraped review content, passes it through a backend API that orchestrates the multi-agent AI pipeline, and returns structured insights that can be displayed in a simple frontend.

The architecture is designed in layers so that the frontend, backend API, AI analysis, and future data ingestion can evolve independently.

---

## 2. High-Level Architecture

### Core Layers
1. **Presentation Layer**
   - Minimal public web UI where users can paste reviews and view results
   - Handles input validation, loading state, and error display

2. **API / Workflow Layer**
   - Backend API server acts as the orchestration layer and API entry point
   - Receives analysis requests and manages the execution of AI agents

3. **AI Analysis Layer**
   - Multiple specialized agents perform focused analysis tasks
   - A final insight agent synthesizes all findings into a unified report

4. **Data Ingestion Layer**
   - Initial version uses manually pasted text
   - Future versions can add CSV uploads, API pulls, and scraping from public sources

5. **Storage & Logging Layer**
   - Optional storage for results, sample datasets, and analysis history
   - Useful for debugging, demos, and analytics

---

## 3. Detailed Component Architecture

### 3.1 Frontend

Purpose:
- Provide a simple interface for end users
- Allow reviewers to submit review text and view the analysis

Components:
- Input textarea for review content
- Buttons for sample review loading and analysis submission
- Results section with structured insights
- Status/error messages for validation and API failures

Technology Options:
- HTML, CSS, JavaScript for a lightweight MVP
- Optional React or Next.js if stronger UI interactivity is needed
- Deployment on Vercel or Netlify

Responsibilities:
- Validate input length before sending
- Show loading indicator during analysis
- Call the backend API endpoint
- Render the returned JSON into readable sections

---

### 3.2 API / Orchestration Layer

Purpose:
- Receive incoming requests from the frontend
- Orchestrate the analysis workflow in a controlled sequence

Primary Tool:
- Backend API server

Responsibilities:
- Accept review text via webhook-style API endpoint
- Validate request payload
- Build agent prompts and call the LLM
- Parse and validate the JSON response from the LLM
- Return final structured JSON to the frontend
- Handle failure cases with meaningful error responses

Workflow Flow:
1. Frontend sends review text to the backend API
2. Backend validates the input
3. Backend executes the agent pipeline
4. Agent outputs are collected and synthesized
5. Final JSON is returned to the frontend

---

### 3.3 AI Agent Layer

Purpose:
- Break the problem into focused sub-tasks instead of using one large prompt
- Improve accuracy and maintainability of output

#### Agent 1: Sentiment Agent
- Classifies review sentiment as Happy, Neutral, or Angry
- Helps identify overall satisfaction or dissatisfaction patterns

#### Agent 2: Pain Point Agent
- Extracts recurring user frustrations related to discovery, recommendations, playlists, and search
- Categorizes issues into structured themes

#### Agent 3: User Segment Agent
- Detects which user groups are represented in the text
- Examples: Student, Gym User, Parent, Casual Listener, Audiophile

#### Agent 4: Feature Request Agent
- Extracts product asks and unmet needs
- Distinguishes between needs, wants, and missing features

#### Agent 5: Insight Agent
- Aggregates outputs from Agents 1–4
- Produces the final rendered JSON structure for the frontend
- Maps findings to the UI sections such as Pain Points, Top Complaints, Feature Requests, and Recommended Opportunities

LLM Options:
- OpenAI GPT-4o / GPT-4.1 mini
- Anthropic Claude
- Either can be used depending on availability, cost, and prompt quality

---

### 3.4 Data Ingestion Layer

Purpose:
- Expand the system beyond pasted text into broader review collection

Initial Scope:
- Manual paste from frontend

Future Scope:
- CSV upload of review datasets
- API-based collection from app stores, forums, or social platforms
- Scheduled scraping from public review pages

Supporting Tools:
- Playwright for browser automation and dynamic page scraping
- Apify for scalable public-data collection workflows
- BeautifulSoup for lightweight HTML parsing

---

### 3.5 Storage and Logging Layer

Purpose:
- Store analysis outputs and optionally raw input for future review

Possible Use Cases:
- Save past analyses for comparison over time
- Store example datasets for demo purposes
- Log workflow failures and latency

Optional Technologies:
- Supabase or Firebase for lightweight storage
- Simple JSON files for early prototypes

---

## 4. End-to-End Data Flow

### Request Flow
1. User opens the frontend page
2. User pastes review text or loads a sample
3. Frontend validates the input
4. Frontend sends the payload to the backend API
5. Backend validates and routes the request to the AI workflow
6. Agents run and generate structured outputs
7. Insight Agent combines the outputs into a final response
8. Backend returns JSON to the frontend
9. Frontend displays results in the appropriate sections

### Error Flow
- Empty input returns a clear validation error
- LLM or workflow failures return a structured error message
- Input size limits prevent excessive cost or latency
- Frontend presents friendly user-facing failure states

---

## 5. Output Schema

The final JSON returned by the Insight Agent should be structured so the frontend can render it consistently.

Example structure:

```json
{
  "sentiment": {
    "overall": "Neutral",
    "summary": "Users express mixed emotions about discovery features"
  },
  "pain_points": [
    {
      "category": "Recommendation issue",
      "detail": "Suggestions feel repetitive"
    }
  ],
  "user_segments": [
    {
      "segment": "Casual Listener",
      "evidence": "Background listening and low engagement"
    }
  ],
  "feature_requests": [
    {
      "type": "Need",
      "request": "More diverse recommendations"
    }
  ],
  "unmet_needs": [
    {
      "need": "Better discovery beyond familiar artists"
    }
  ],
  "recommended_opportunities": [
    {
      "opportunity": "Introduce exploration-focused playlists"
    }
  ]
}
```

---

## 6. Security and Reliability Considerations

- Keep the public demo simple and safe by avoiding user authentication in the MVP
- Validate and limit input size to control cost and latency
- Use CORS configuration so the deployed frontend can call the webhook
- Add timeout handling and fallback errors for LLM failures
- Keep the output schema fixed to prevent frontend breakage

---

## 7. Phase-wise Implementation Plan

### Phase 1: MVP
- Build single-page frontend
- Create backend API endpoint
- Implement one basic analysis flow
- Return structured JSON

### Phase 2: Multi-Agent Analysis
- Add the five AI agents
- Ensure parallel execution where possible
- Validate output schema

### Phase 3: Frontend Integration
- Render all result sections clearly
- Add loading and error states
- Test the end-to-end user flow

### Phase 4: Expansion and Scaling
- Add scraping and ingestion tools
- Support larger datasets and scheduled processing
- Improve persistence and analytics

---

## 8. Recommended Tech Stack Summary

- **Workflow Orchestration:** Backend API server
- **AI Models:** OpenAI GPT-4o / GPT-4.1 mini or Anthropic Claude
- **Frontend:** HTML/CSS/JavaScript, optionally React or Next.js
- **Deployment:** Vercel or Netlify
- **Scraping:** Playwright, Apify, BeautifulSoup
- **Storage:** Supabase/Firebase or JSON-based storage
- **Optional Intelligence:** LangChain or Semantic Kernel for advanced orchestration

