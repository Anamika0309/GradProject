# Phase 5 – Deployment and Public Access

> **Status: Not started — awaiting Phase 4 completion**

This phase makes the system publicly accessible for senior reviewer demos:

- Deploy frontend to Vercel or Netlify (static hosting)
- Deploy backend API to a public host or server
- Configure CORS to allow the deployed frontend origin
- Set environment variables (LLM API keys, API credentials)
- Validate the full public flow end-to-end from a fresh browser session

## Planned Structure

```
phase-5/
  deployment/
    vercel.json             # Vercel deployment config
    .env.example            # Environment variable template
    cors-config.md          # CORS setup instructions for the backend API
  docs/
    README.md               # This file
    deployment-checklist.md # Pre-launch checklist
```

## Deployment Targets

| Layer | Platform |
|---|---|
| Frontend | Vercel / Netlify |
| Backend API | Public host or server |
| LLM | OpenAI / Anthropic with environment credentials |
