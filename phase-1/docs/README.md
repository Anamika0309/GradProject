# Phase 1 – Project Setup and MVP Foundation

This folder contains the complete Phase 1 implementation of the **AI-Powered Review Discovery Engine** for Spotify.

---

## What's in this Phase

| Path | Purpose |
|---|---|
| `frontend/index.html` | Single-page web app UI |
| `frontend/style.css` | Spotify-themed dark mode design system |
| `frontend/app.js` | Input validation, API call, result rendering |
| `backend/server.js` | Mock backend analysis API (Express) |
| `backend/package.json` | Node dependencies |
| `backend/workflow-mvp.json` | (Removed) n8n workflow file |
| `sample-data/reviews.json` | 10 realistic Spotify user reviews |
| `docs/README.md` | This file |

---

## Quick Start

### 1. Start the Backend (Mock Webhook)

```bash
cd phase-1/backend
npm install
npm run dev
```

The server will start at **http://localhost:5678**

Test it is running:
```bash
curl http://localhost:5678/
```

### 2. Open the Frontend

Open `phase-1/frontend/index.html` directly in your browser. No build step required.

> **Tip**: If your browser blocks `fetch` to localhost due to CORS or security settings, use VS Code Live Server, or serve the files with:
> ```bash
> npx serve phase-1/frontend
> ```

---

## Testing the MVP

### Happy Path
1. Open `index.html` in a browser.
2. Click **Load Sample Reviews** — textarea should fill with Spotify reviews.
3. Click **Analyze Reviews** — loading animation should appear.
4. The Results panel should appear with a **Phase 1 Success** banner and all six pending cards.

### Validation Tests

| Scenario | Expected Behaviour |
|---|---|
| Submit empty textarea | Red validation message appears, no request sent |
| Input > 5,000 chars | Red error showing character count, no request sent |
| Backend not running | Error card: "Could not reach the analysis server" |
| Valid input, server running | Phase 1 success banner + 6 result cards (all pending Phase 2) |

### API Tests (curl)

```bash
# Success case
curl -s -X POST http://localhost:5678/webhook/analyze \
  -H "Content-Type: application/json" \
  -d '{"reviews":"I love Spotify but the recommendations are broken"}' | python -m json.tool

# Empty input
curl -s -X POST http://localhost:5678/webhook/analyze \
  -H "Content-Type: application/json" \
  -d '{"reviews":""}' | python -m json.tool

# Oversized input (generate a long string)
python -c "import json; print(json.dumps({'reviews': 'a'*5001}))" | \
  curl -s -X POST http://localhost:5678/webhook/analyze \
  -H "Content-Type: application/json" \
  -d @- | python -m json.tool
```

---

## Backend API Setup

This phase uses a direct backend API instead of an external workflow tool.

1. Start the backend server in `phase-1/backend`:
```bash
cd phase-1/backend
npm install
npm run dev
```
2. The backend will listen at `http://localhost:5678`.
3. Point `phase-1/frontend/app.js` to `http://localhost:5678/webhook/analyze`.

---

## Phase 1 Success Criteria

- [x] Project folder structure created
- [x] Frontend page loads successfully
- [x] Review text input available with character counter
- [x] Load Sample Reviews button populates textarea
- [x] Analyze Reviews button shows loading state
- [x] Backend mock webhook responds at `POST /webhook/analyze`
- [x] Empty input returns HTTP 400 with clear error
- [x] Oversized input returns HTTP 400 with character count
- [x] Successful submission returns Phase 1 JSON schema
- [x] Frontend renders all six result card sections
- [x] backend API mock server provided

---

## Next Phase

**Phase 2** will wire the five AI agents (Sentiment, Pain Point, User Segment, Feature Request, Insight) into the backend API, replacing the mock server response with real LLM calls.

See [`../phase-2/`](../phase-2/) for implementation.
