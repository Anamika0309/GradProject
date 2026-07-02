# Project Decisions Log

This file records the important decisions taken while designing and planning the AI-Powered Review Discovery Engine.

---

## 1. Decision: Use a Multi-Agent AI Workflow

**Decision:** Build the analysis system as a multi-agent workflow instead of a single monolithic prompt.

**Reason:**
- Improves clarity and maintainability
- Allows each agent to focus on a specific task
- Makes the system easier to debug and extend
- Aligns with the problem statement’s recommended architecture

**Impact:**
- The workflow is divided into Sentiment, Pain Point, User Segment, Feature Request, and Insight agents.

---

## 2. Decision: Use Backend API for Workflow Orchestration

**Decision:** Use a backend API server as the orchestration layer for the analysis workflow.

**Reason:**
- Easier to manage directly in code
- Good for webhook-style API automation
- Simplifies orchestration of multiple AI steps
- Suitable for a demo and rapid prototyping

**Impact:**
- The system uses a webhook-triggered workflow instead of a custom backend server in the initial version.

---

## 3. Decision: Keep the Frontend Minimal for the MVP

**Decision:** Use a simple single-page interface with no login and minimal styling in the first version.

**Reason:**
- Focuses on proving the core workflow
- Makes the demo easy to use and quick to deploy
- Aligns with the problem statement’s expectation of a public, simple reviewer experience

**Impact:**
- The frontend includes only text input, sample review loading, analyze action, and result display.

---

## 4. Decision: Start with Pasted Review Text as Input

**Decision:** For the initial build, accept review text pasted directly into the frontend.

**Reason:**
- Simplifies the first version
- Avoids dependency on scraping or external data sources early
- Allows the team to validate the AI workflow quickly

**Impact:**
- The MVP focuses on analysis quality and workflow reliability before adding ingestion complexity.

---

## 5. Decision: Use Structured JSON as the Output Format

**Decision:** Require each agent and the final insight output to return structured JSON.

**Reason:**
- Makes it easier for the frontend to render results
- Reduces risk of malformed or inconsistent outputs
- Supports reliable downstream processing

**Impact:**
- The frontend can render sections consistently and predictably.

---

## 6. Decision: Use LLMs for Specialized Analysis Tasks

**Decision:** Use LLMs such as GPT-4o / GPT-4.1 mini or Claude for each specialized agent.

**Reason:**
- Strong performance for summarization and classification tasks
- Suitable for extracting categories, sentiments, and product asks from natural language
- Flexible for prompt-based agent design

**Impact:**
- Each agent performs one focused task instead of one broad analysis prompt.

---

## 7. Decision: Add Input Limits for Cost and Latency Control

**Decision:** Enforce input length limits in the workflow and frontend.

**Reason:**
- Keeps the public demo affordable
- Reduces long response times
- Avoids overloading the LLM workflow with very large inputs

**Impact:**
- The system shows validation messages for oversized review input.

---

## 8. Decision: Prioritize Demo Readiness Over Full Production Complexity

**Decision:** Keep the first version lightweight and demo-friendly rather than fully production-grade.

**Reason:**
- The main goal is to prove the concept end to end
- Reduce complexity in the initial release
- Make it easier to showcase to reviewers and stakeholders

**Impact:**
- Authentication, advanced analytics, and complex infrastructure are deferred to later phases.

---

## 9. Decision: Plan for Future Scraping and Data Ingestion

**Decision:** Design the architecture so that additional ingestion sources can be added later.

**Reason:**
- The problem statement mentions multiple review sources
- The system should scale beyond manually pasted text
- Future ingestion can be added as new modules without changing the core analysis flow

**Impact:**
- The architecture includes planned support for CSV upload, APIs, and scraping.

---

## 10. Decision: Use a Fixed Result Schema for the Frontend

**Decision:** Ensure the final output schema maps directly to the frontend result sections.

**Reason:**
- Prevents frontend breakage from malformed or inconsistent output
- Makes the presentation layer simple and predictable
- Aligns with the expected results structure from the problem statement

**Impact:**
- The final output will support sections such as Pain Points, Top Complaints, User Segments, Feature Requests, and Unmet Needs.

---

## 11. Decision: Keep Error Handling Simple but Clear

**Decision:** Return clear error messages for empty input, workflow failure, or LLM issues.

**Reason:**
- Improves demo reliability
- Helps users understand what went wrong
- Makes debugging easier during development

**Impact:**
- The frontend shows loading, success, and error states clearly.

---

## 12. Decision: Use Deployment Platforms Suitable for Quick Demo Launch

165:**Decision:** Use Vercel or Netlify for the frontend and a publicly accessible backend API for the backend workflow.

**Reason:**
- Fast deployment for a demo
- Low complexity compared to setting up a custom backend from scratch
- Suitable for a public proof-of-concept

**Impact:**
- The system can be launched quickly and demonstrated externally.

---

## 13. Decision: Keep the Architecture Modular

**Decision:** Separate frontend, orchestration, AI analysis, ingestion, and storage responsibilities.

**Reason:**
- Easier to maintain
- Easier to test each phase independently
- Supports future feature expansion

**Impact:**
- The project can evolve from an MVP to a more advanced analytics platform without major rework.
