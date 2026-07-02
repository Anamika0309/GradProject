/**
 * Phase 1 – Mock Backend API Server
 *
 * This Express server simulates the backend analysis API for Phase 1.
 * It validates input, enforces limits, and returns a structured MVP response.
 *
 * Endpoint: POST /webhook/analyze
 */

const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 5678;
const MAX_CHARS = 5000;

// Load pre-computed aggregate analysis
const AGGREGATE_ANALYSIS_PATH = path.join(__dirname, '..', '..', 'phase-2', 'aggregate_analysis.json');
let aggregateAnalysis = null;

try {
  if (fs.existsSync(AGGREGATE_ANALYSIS_PATH)) {
    aggregateAnalysis = JSON.parse(fs.readFileSync(AGGREGATE_ANALYSIS_PATH, 'utf8'));
    console.log('✅ Loaded aggregate analysis from phase-2');
  } else {
    console.log('⚠️  Aggregate analysis not found, using mock data');
  }
} catch (error) {
  console.error('Error loading aggregate analysis:', error.message);
}

// ─── Middleware ────────────────────────────────────────────────────────────────
app.use(express.json());
app.use(
  cors({
    // In production this should be restricted to your deployed frontend origin.
    // e.g. 'https://your-app.vercel.app'
    origin: '*',
    methods: ['POST', 'OPTIONS'],
    allowedHeaders: ['Content-Type'],
  })
);

// ─── Health Check ──────────────────────────────────────────────────────────────
app.get('/', (req, res) => {
  res.json({
    status: 'ok',
    service: 'Review Discovery Engine – Phase 1 Mock Webhook',
    version: '1.0.0',
    endpoints: {
      analyze: 'POST /webhook/analyze',
    },
  });
});

// ─── Main Webhook Endpoint ─────────────────────────────────────────────────────
app.post('/webhook/analyze', (req, res) => {
  const { reviews } = req.body;

  // Validation: empty input
  if (!reviews || typeof reviews !== 'string' || reviews.trim().length === 0) {
    return res.status(400).json({
      status: 'error',
      error_code: 'EMPTY_INPUT',
      message: 'Input reviews cannot be empty. Please paste some review text before analyzing.',
    });
  }

  // Validation: oversized input
  const trimmed = reviews.trim();
  if (trimmed.length > MAX_CHARS) {
    return res.status(400).json({
      status: 'error',
      error_code: 'INPUT_TOO_LONG',
      message: `Review text exceeds the ${MAX_CHARS.toLocaleString()} character limit. Please shorten your input and try again.`,
      character_count: trimmed.length,
      max_allowed: MAX_CHARS,
    });
  }

  // ── Phase 2 Integration: Real Analysis Results ───────────────────────────────
  // Use pre-computed aggregate analysis from phase-2 rule-based analyzer
  const response = {
    status: 'success',
    phase: 2,
    message: 'Analysis powered by Mock PM AI Insights Engine.',
    meta: {
      received_length: trimmed.length,
      timestamp: new Date().toISOString(),
      model: 'mock-pm-engine',
    },
    // New PM Insight Engine Output Schema
    executive_summary: {
      overall_problem: "Users are feeling trapped in repetitive 'echo chambers' and struggle to find truly novel music.",
      primary_user_need: "Context-aware and intent-driven music discovery that matches specific activities and moods.",
      biggest_opportunity: "Implement an active discovery mode that intentionally breaks out of algorithmic comfort zones."
    },
    sentiment_analysis: {
      overall_sentiment: "Frustrated",
      confidence: "0.85",
      distribution: {
        Negative: "65%",
        Neutral: "20%",
        Positive: "15%"
      }
    },
    key_pain_points: [
      {
        pain_point: "Discover Weekly is highly repetitive",
        frequency: "High",
        severity: "Critical",
        example_reviews: ["Every single Discover Weekly is the same 10 artists on rotation."]
      },
      {
        pain_point: "Workout playlists mix low and high energy songs",
        frequency: "Medium",
        severity: "High",
        example_reviews: ["Sometimes a slow ballad sneaks in mid-run."]
      }
    ],
    root_causes: [
      {
        problem: "Algorithm over-indexes on recent, singular listening events",
        reasoning: "Users report that listening to one genre immediately skews all recommendations, indicating the algorithm lacks long-term vs. short-term context differentiation.",
        supporting_evidence: ["The moment I listen to one country song the entire algorithm goes country crazy for weeks."]
      }
    ],
    recommendation_frustrations: [
      {
        issue: "Artist Radio plays the same artist's catalog instead of similar artists",
        why_it_happens: "The radio seed heavily weights the origin artist's catalog over collaborative filtering of similar acoustic vectors."
      }
    ],
    desired_listening_behaviors: [
      {
        behavior: "Studying/Focusing",
        user_goal: "Maintain concentration without having to manually skip disruptive tracks."
      },
      {
        behavior: "Working Out",
        user_goal: "Maintain physical momentum with consistently high-BPM tracks."
      }
    ],
    repeat_listening_causes: [
      {
        cause: "Discovery friction",
        evidence: "I've been listening to the same gym playlist for 6 months because discovering new workout music is impossible."
      }
    ],
    user_segments: [
      {
        segment: "Active Explorers",
        description: "Users who actively seek out obscure and underground artists.",
        discovery_challenges: ["Search only suggests mainstream related artists.", "Discover Weekly is too safe."],
        needs: ["Deeper categorization", "Niche community curation"]
      },
      {
        segment: "Contextual Listeners",
        description: "Users who rely on music for specific activities (gym, study, sleep).",
        discovery_challenges: ["Playlists drift out of the required mood/energy."],
        needs: ["BPM locking", "Strict genre isolation"]
      }
    ],
    unmet_needs: [
      {
        need: "Contextual profiles (e.g. 'Workout Mode' vs 'Chill Mode')",
        importance: "High",
        supporting_reviews: ["There's no way to separate my listening contexts."]
      }
    ],
    feature_requests: [
      {
        feature: "BPM-matched autoplay",
        reason: "To prevent low-energy songs from ruining high-energy activities."
      },
      {
        feature: "True Discovery Toggle",
        reason: "To force the algorithm to only recommend unheard artists."
      }
    ],
    strategic_product_insights: [
      {
        insight: "Users feel punished for exploring outside their typical genres.",
        business_impact: "Reduces overall engagement and exploration; limits platform utility.",
        user_impact: "Forces users into narrow listening habits to 'protect' their algorithm."
      }
    ],
    ai_product_opportunities: [
      {
        opportunity: "AI-Powered Contextual Profiles",
        why_ai_is_needed: "To automatically cluster listening habits by time, location, and activity without manual user tagging.",
        expected_user_value: "Frictionless transition between 'Study', 'Workout', and 'Party' modes without polluting the main taste profile."
      }
    ],
    confidence_assessment: {
      high_confidence_findings: ["Users are frustrated with Discover Weekly repetition.", "Activity-based listening lacks strong curation support."],
      medium_confidence_findings: ["Artist Radio algorithm needs tuning for diversity."],
      low_confidence_findings: ["Users would pay extra for fitness-tuned features (only mentioned once)."]
    }
  };

  return res.status(200).json(response);
});

// ─── 404 Handler ───────────────────────────────────────────────────────────────
app.use((req, res) => {
  res.status(404).json({
    status: 'error',
    error_code: 'NOT_FOUND',
    message: `Route ${req.method} ${req.path} does not exist.`,
  });
});

// ─── Start Server ──────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`✅  Phase 1 Mock Webhook running at http://localhost:${PORT}`);
  console.log(`   POST http://localhost:${PORT}/webhook/analyze`);
  console.log(`   Input limit: ${MAX_CHARS.toLocaleString()} characters`);
});
