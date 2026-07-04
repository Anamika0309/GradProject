/**
 * Phase 1 – Frontend Application Logic
 * Review Discovery Engine
 */

'use strict';

// ─── Configuration ─────────────────────────────────────────────────────────────
// ⚠️ DEPLOYMENT INSTRUCTIONS ⚠️
// When deploying to Render, change this from 'http://localhost:5678' to your Render URL:
// Example: const API_HOST = 'https://ai-product-insights.onrender.com';
const API_HOST = 'https://ai-product-insights.onrender.com';

const CONFIG = {
  MAX_CHARS: 5000,
  WARN_THRESHOLD: 0.8,   // 80% of max → show warning colour
  WEBHOOK_URL: `${API_HOST}/webhook/analyze`,
  DATASET_WEBHOOK_URL: `${API_HOST}/webhook/analyze-dataset`,
};

// ─── Sample Reviews ───────────────────────────────────────────────────────────
const SAMPLE_REVIEWS = [
  `I've been using Spotify for 3 years and the recommendations have gotten worse over time. Every single Discover Weekly is the same 10 artists on rotation. It's like the algorithm just gave up trying to learn my taste.`,
  `The radio feature is broken for me. Whenever I start a song radio it just plays the same artist's entire discography. I want to discover similar artists, not just more of the same person. A proper discovery mode would be amazing.`,
  `The playlist curation has become a joke. I added a classical music playlist and now my Discover Weekly is full of orchestral pieces when I'm trying to find new indie rock. There's no way to separate my listening contexts.`,
  `Needs a better workout mode. I want high BPM tracks but the workout playlists are all over the place. The energy matching is terrible — sometimes a slow ballad sneaks in mid-run. I'd pay extra for a fitness-tuned discovery feature.`,
  `My kids keep getting exposed to explicit lyrics even when I filter them out. The family plan doesn't respect the content filter properly. This needs to be fixed urgently.`,
  `I feel like Spotify punishes you for having diverse taste. The moment I listen to one country song the entire algorithm goes country crazy for weeks. I want it to understand I was in a specific mood, not that I converted overnight.`,
  `Search is completely broken for obscure artists. Real music fans want to go deeper, not broader. The related artist suggestions are always mainstream names with nothing in common except genre.`,
  `Please add a study mode that learns from what I listen to while studying. Right now I have to manually curate everything. Even basic context awareness like time of day would improve this a lot.`,
  `I've been listening to the same gym playlist for 6 months because discovering new workout music is impossible. The autoplay after my playlist ends always picks slow songs. BPM matching would be a game changer.`,
  `What happened to the old Discover Weekly? It used to feel fresh and surprising. Now it feels like it just gives me popular artists in whatever genres I've listened to recently. I miss discovering bands I never would have found on my own.`,
];

// ─── DOM References ────────────────────────────────────────────────────────────
const els = {
  textarea: document.getElementById('review-input'),
  charCounter: document.getElementById('char-counter'),
  loadSampleBtn: document.getElementById('btn-load-sample'),
  analyzeBtn: document.getElementById('btn-analyze'),
  analyzeDatasetBtn: document.getElementById('btn-analyze-dataset'),
  sampleSizeSlider: document.getElementById('sample-size-slider'),
  sampleSizeVal: document.getElementById('sample-size-val'),
  mapReduceWarning: document.getElementById('map-reduce-warning'),
  validationMsg: document.getElementById('validation-message'),
  loadingIndicator: document.getElementById('loading-indicator'),
  resultsSection: document.getElementById('results-section'),
  resultsTimestamp: document.getElementById('results-timestamp'),
  resultsCharCount: document.getElementById('results-char-count'),
  analyticsDashboard: document.getElementById('analytics-dashboard'),
  btnExportJson: document.getElementById('btn-export-json'),
  btnExportPdf: document.getElementById('btn-export-pdf'),
};

// ─── State ─────────────────────────────────────────────────────────────────────
let isLoading = false;
let currentReportData = null; // Store latest data for exports
let chartInstances = {}; // Store chart instances to destroy on re-render

// ─── Helpers ───────────────────────────────────────────────────────────────────
function formatTimestamp(isoString) {
  try {
    return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return isoString;
  }
}

function showValidation(message, type = 'error') {
  els.validationMsg.textContent = message;
  els.validationMsg.className = `validation-message ${type}`;
}

function hideValidation() {
  els.validationMsg.className = 'validation-message';
}

function setLoading(active, isMapReduce = false) {
  isLoading = active;
  els.analyzeBtn.classList.toggle('loading', active);
  els.analyzeDatasetBtn.classList.toggle('loading', active);
  els.analyzeBtn.disabled = active;
  els.analyzeDatasetBtn.disabled = active;
  els.loadSampleBtn.disabled = active;
  els.textarea.disabled = active;
  els.sampleSizeSlider.disabled = active;

  const loadingTitle = els.loadingIndicator.querySelector('.loading-title');
  const loadingSubtitle = els.loadingIndicator.querySelector('.loading-subtitle');

  if (active) {
    if (isMapReduce) {
      els.analyzeDatasetBtn.innerHTML = `<span class="spinner"></span> Running Map-Reduce…`;
      loadingTitle.textContent = "Processing Large Dataset...";
      loadingSubtitle.textContent = "Map-Reduce Chunking is active. This will take several minutes to respect API rate limits. Please don't close this page.";
      loadingTitle.style.color = "#f5a623";
    } else {
      els.analyzeBtn.innerHTML = `<span class="spinner"></span> Analyzing…`;
      loadingTitle.textContent = "Analyzing your reviews…";
      loadingSubtitle.textContent = "Our AI agents are processing your input. This may take a few seconds.";
      loadingTitle.style.color = "var(--text-primary)";
    }

    els.loadingIndicator.classList.add('visible');
    els.resultsSection.classList.remove('visible');
    animateLoadingSteps();
  } else {
    els.analyzeBtn.innerHTML = `<span>✦</span> Analyze Pasted Reviews`;
    els.analyzeDatasetBtn.innerHTML = `<span>📊</span> Analyze Dataset`;
    els.loadingIndicator.classList.remove('visible');
  }
}

let stepTimer = null;
function animateLoadingSteps() {
  const steps = els.loadingIndicator.querySelectorAll('.loading-step');
  let i = 0;
  clearInterval(stepTimer);
  steps.forEach(s => s.classList.remove('active'));
  if (steps.length) steps[0].classList.add('active');
  stepTimer = setInterval(() => {
    steps[i]?.classList.remove('active');
    i = (i + 1) % steps.length;
    steps[i]?.classList.add('active');
  }, 1200);
}

// ─── Character Counter ──────────────────────────────────────────────────────────
function updateCharCounter() {
  const len = els.textarea.value.length;
  const pct = len / CONFIG.MAX_CHARS;
  els.charCounter.textContent = `${len.toLocaleString()} / ${CONFIG.MAX_CHARS.toLocaleString()}`;
  els.charCounter.className = 'char-counter' +
    (pct >= 1 ? ' at-limit' : pct >= CONFIG.WARN_THRESHOLD ? ' near-limit' : '');
}

// ─── Render Results ────────────────────────────────────────────────────────────
function renderSuccess(data) {
  clearInterval(stepTimer);

  // Update meta chips
  els.resultsTimestamp.textContent = formatTimestamp(data.meta?.timestamp || new Date().toISOString());
  els.resultsCharCount.textContent = `${data.meta?.received_length?.toLocaleString() || '—'} chars`;

  // Populate new PM cards

  // 1. Executive Summary
  if (data.executive_summary) {
    document.getElementById('out-exec-summary').innerHTML = `
      <div style="margin-bottom: 12px;"><strong>Overall Problem:</strong> ${data.executive_summary.overall_problem || '—'}</div>
      <div style="margin-bottom: 12px;"><strong>Primary Need:</strong> ${data.executive_summary.primary_user_need || '—'}</div>
      <div><strong>Biggest Opportunity:</strong> ${data.executive_summary.biggest_opportunity || '—'}</div>
    `;
  }



  // 4. Root Causes
  if (data.root_causes && data.root_causes.length) {
    document.getElementById('out-root-causes').innerHTML = `
      <ul style="padding-left: 20px; margin: 0;">
        ${data.root_causes.map(r => `
          <li style="margin-bottom: 8px;">
            <strong>${r.problem}</strong>
            <div style="margin-top: 4px;">${r.reasoning}</div>
          </li>
        `).join('')}
      </ul>
    `;
  } else { document.getElementById('out-root-causes').innerHTML = 'None detected.'; }

  // 5. Recommendation Frustrations
  if (data.recommendation_frustrations && data.recommendation_frustrations.length) {
    document.getElementById('out-rec-frustrations').innerHTML = `
      <ul style="padding-left: 20px; margin: 0;">
        ${data.recommendation_frustrations.map(f => `
          <li style="margin-bottom: 8px;"><strong>${f.issue}:</strong> ${f.why_it_happens}</li>
        `).join('')}
      </ul>
    `;
  } else { document.getElementById('out-rec-frustrations').innerHTML = 'None detected.'; }

  // 6. Desired Listening Behaviors
  if (data.desired_listening_behaviors && data.desired_listening_behaviors.length) {
    document.getElementById('out-behaviors').innerHTML = `
      <ul style="padding-left: 20px; margin: 0;">
        ${data.desired_listening_behaviors.map(b => `
          <li style="margin-bottom: 8px;"><strong>${b.behavior}:</strong> ${b.user_goal}</li>
        `).join('')}
      </ul>
    `;
  } else { document.getElementById('out-behaviors').innerHTML = 'None detected.'; }

  // 7. Repeat Listening Causes
  if (data.repeat_listening_causes && data.repeat_listening_causes.length) {
    document.getElementById('out-repeat-causes').innerHTML = `
      <ul style="padding-left: 20px; margin: 0;">
        ${data.repeat_listening_causes.map(c => `
          <li style="margin-bottom: 8px;"><strong>${c.cause}:</strong> ${c.evidence}</li>
        `).join('')}
      </ul>
    `;
  } else { document.getElementById('out-repeat-causes').innerHTML = 'None detected.'; }

  // 8. User Segments
  if (data.user_segments && data.user_segments.length) {
    document.getElementById('out-segments').innerHTML = `
      <ul style="padding-left: 20px; margin: 0;">
        ${data.user_segments.map(s => `
          <li style="margin-bottom: 12px;">
            <strong>${s.segment}</strong> - ${s.description}
            <div style="font-size: 0.9em; margin-top: 4px;"><strong>Needs:</strong> ${(s.needs || []).join(', ')}</div>
          </li>
        `).join('')}
      </ul>
    `;
  } else { document.getElementById('out-segments').innerHTML = 'None detected.'; }

  // 9. Unmet Needs
  if (data.unmet_needs && data.unmet_needs.length) {
    document.getElementById('out-needs').innerHTML = `
      <ul style="padding-left: 20px; margin: 0;">
        ${data.unmet_needs.map(n => `
          <li style="margin-bottom: 8px;"><strong>${n.need}</strong> (Importance: ${n.importance})</li>
        `).join('')}
      </ul>
    `;
  } else { document.getElementById('out-needs').innerHTML = 'None detected.'; }

  // 10. Feature Requests
  if (data.feature_requests && data.feature_requests.length) {
    document.getElementById('out-features').innerHTML = `
      <ul style="padding-left: 20px; margin: 0;">
        ${data.feature_requests.map(f => `
          <li style="margin-bottom: 8px;"><strong>${f.feature}:</strong> ${f.reason}</li>
        `).join('')}
      </ul>
    `;
  } else { document.getElementById('out-features').innerHTML = 'None detected.'; }

  // 11. Strategic Product Insights
  if (data.strategic_product_insights && data.strategic_product_insights.length) {
    document.getElementById('out-strategic').innerHTML = `
      <ul style="padding-left: 20px; margin: 0;">
        ${data.strategic_product_insights.map(i => `
          <li style="margin-bottom: 12px;">
            <strong>${i.insight}</strong>
            <div style="font-size: 0.9em; margin-top: 4px;"><strong>Biz Impact:</strong> ${i.business_impact}</div>
          </li>
        `).join('')}
      </ul>
    `;
  } else { document.getElementById('out-strategic').innerHTML = 'None detected.'; }

  // 12. AI Product Opportunities
  if (data.ai_product_opportunities && data.ai_product_opportunities.length) {
    document.getElementById('out-opportunities').innerHTML = `
      <ul style="padding-left: 20px; margin: 0;">
        ${data.ai_product_opportunities.map(o => `
          <li style="margin-bottom: 12px;">
            <strong>${o.opportunity}</strong>
            <div style="font-size: 0.9em; margin-top: 4px; color: var(--color-brand);"><strong>Why AI:</strong> ${o.why_ai_is_needed}</div>
          </li>
        `).join('')}
      </ul>
    `;
  } else { document.getElementById('out-opportunities').innerHTML = 'None detected.'; }

  // 13. Confidence Assessment
  if (data.confidence_assessment) {
    const ca = data.confidence_assessment;
    document.getElementById('out-confidence').innerHTML = `
      <div style="margin-bottom: 8px;"><strong>High:</strong> ${(ca.high_confidence_findings || []).join(', ') || 'None'}</div>
      <div style="margin-bottom: 8px;"><strong>Medium:</strong> ${(ca.medium_confidence_findings || []).join(', ') || 'None'}</div>
      <div><strong>Low:</strong> ${(ca.low_confidence_findings || []).join(', ') || 'None'}</div>
    `;
  } else { document.getElementById('out-confidence').innerHTML = 'None provided.'; }

  // Phase 1 status banner is already in HTML; show it.
  const phaseBanner = document.getElementById('phase-banner');
  if (phaseBanner) phaseBanner.style.display = 'flex';

  // Show the results section with animation
  els.resultsSection.style.display = 'block';

  currentReportData = data;
  renderCharts(data); // Phase 7: Render charts

  requestAnimationFrame(() => {
    els.resultsSection.classList.add('visible');
  });

  // Scroll into view smoothly
  setTimeout(() => els.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
}

function renderError(message) {
  clearInterval(stepTimer);

  const container = document.getElementById('results-cards');
  if (!container) return;

  container.innerHTML = `
    <div class="error-card">
      <div class="error-card-icon">⚠️</div>
      <div>
        <p class="error-card-title">Analysis Failed</p>
        <p class="error-card-body">${message}</p>
      </div>
    </div>`;

  const phaseBanner = document.getElementById('phase-banner');
  if (phaseBanner) phaseBanner.style.display = 'none';

  els.resultsSection.style.display = 'block';
  requestAnimationFrame(() => els.resultsSection.classList.add('visible'));
  setTimeout(() => els.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
}

// ─── Load Sample Reviews ───────────────────────────────────────────────────────
let sampleIndex = 0;
function loadSampleReview() {
  // Cycle through all samples one by one
  const sample = SAMPLE_REVIEWS.slice(0, 5).join('\n\n---\n\n');
  els.textarea.value = sample;
  updateCharCounter();
  hideValidation();
  els.textarea.focus();
}

// ─── Main Analysis Flow ─────────────────────────────────────────────────────────
async function analyzeReviews() {
  hideValidation();

  const text = els.textarea.value.trim();

  // Frontend validations
  if (!text) {
    showValidation('⚠️  Please paste review text or click "Load Sample Reviews" before analyzing.', 'error');
    return;
  }
  if (text.length > CONFIG.MAX_CHARS) {
    showValidation(
      `⚠️  Your input is ${text.length.toLocaleString()} characters, which exceeds the ${CONFIG.MAX_CHARS.toLocaleString()}-character limit. Please shorten your review text.`,
      'error'
    );
    return;
  }

  setLoading(true);

  try {
    const response = await fetch(CONFIG.WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reviews: text }),
    });

    const data = await response.json();

    if (!response.ok || data.status === 'error') {
      const msg = data.message || `Server returned status ${response.status}. Please try again.`;
      renderError(msg);
    } else {
      renderSuccess(data);
    }
  } catch (err) {
    console.error('[ReviewEngine] Fetch error:', err);
    if (err instanceof TypeError && err.message.includes('fetch')) {
      renderError(
        'Could not reach the analysis server. The backend might have timed out or is sleeping. ' +
        'Please wait a moment and try again.'
      );
    } else {
      renderError('An unexpected error occurred. Check the browser console for more details.');
    }
  } finally {
    setLoading(false);
  }
}

// ─── Dataset Analysis Flow ───────────────────────────────────────────────────────
async function analyzeDataset() {
  hideValidation();

  const sampleSize = parseInt(els.sampleSizeSlider.value, 10);
  const isMapReduce = sampleSize > 100;

  setLoading(true, isMapReduce);

  try {
    const response = await fetch(CONFIG.DATASET_WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sample_size: sampleSize }),
    });

    const data = await response.json();

    if (!response.ok || data.status === 'error') {
      const msg = data.message || `Server returned status ${response.status}. Please try again.`;
      renderError(msg);
    } else {
      renderSuccess(data);
    }
  } catch (err) {
    console.error('[ReviewEngine] Fetch error:', err);
    if (err instanceof TypeError && err.message.includes('fetch')) {
      renderError(
        'Could not reach the analysis server. Make sure the backend is running on <code>localhost:5678</code>. ' +
        'Run <strong>python phase-2/server.py</strong> to start the backend.'
      );
    } else {
      renderError('An unexpected error occurred. Check the browser console for more details.');
    }
  } finally {
    setLoading(false);
  }
}

// ─── Phase 7: Charts & Exports ──────────────────────────────────────────────
function renderCharts(data) {
  els.analyticsDashboard.style.display = 'grid';

  // Destroy old instances
  if (chartInstances.sentiment) chartInstances.sentiment.destroy();
  if (chartInstances.painPoints) chartInstances.painPoints.destroy();

  // 1. Sentiment Chart
  const sentimentCtx = document.getElementById('sentimentChart').getContext('2d');
  let sLabels = ['Negative', 'Neutral', 'Positive'];
  let sData = [90, 5, 5]; // Fallback values

  if (data.sentiment_analysis?.distribution) {
    sLabels = Object.keys(data.sentiment_analysis.distribution);
    sData = sLabels.map(k => parseInt(data.sentiment_analysis.distribution[k]) || 0);
  }

  chartInstances.sentiment = new Chart(sentimentCtx, {
    type: 'doughnut',
    data: {
      labels: sLabels,
      datasets: [{
        data: sData,
        backgroundColor: ['#ef4444', '#94a3b8', '#22c55e'],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { color: '#a0a0a0' } }
      }
    }
  });

  // 2. Pain Points Chart
  const painCtx = document.getElementById('painPointsChart').getContext('2d');
  let pLabels = ['Technical', 'Ads', 'Features'];
  let pData = [10, 8, 5]; // Fallback

  if (data.key_pain_points && data.key_pain_points.length > 0) {
    pLabels = data.key_pain_points.map(p => {
      // truncate long labels
      return p.pain_point.length > 20 ? p.pain_point.substring(0, 20) + '...' : p.pain_point;
    });
    // Convert frequency to arbitrary numerical values for visual scale
    pData = data.key_pain_points.map(p => {
      let f = p.frequency?.toLowerCase() || 'medium';
      return f === 'high' ? 3 : f === 'medium' ? 2 : 1;
    });
  }

  chartInstances.painPoints = new Chart(painCtx, {
    type: 'bar',
    data: {
      labels: pLabels,
      datasets: [{
        label: 'Frequency Level',
        data: pData,
        backgroundColor: '#1db954',
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          ticks: { color: '#a0a0a0', stepSize: 1 },
          grid: { color: '#333' }
        },
        x: { ticks: { color: '#a0a0a0' }, grid: { display: false } }
      },
      plugins: {
        legend: { display: false }
      }
    }
  });
}

els.btnExportJson.addEventListener('click', () => {
  if (!currentReportData) return;
  const blob = new Blob([JSON.stringify(currentReportData, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `ai_insights_${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
});

els.btnExportPdf.addEventListener('click', () => {
  if (!currentReportData) return;

  els.btnExportPdf.innerHTML = '<span class="spinner"></span> Generating...';

  let html = `<div style="background-color: #fff; color: #000; font-family: Arial, sans-serif; padding: 40px; font-size: 14px; line-height: 1.6; width: 800px; box-sizing: border-box;">`;
  html += `<h1 style="font-size: 24px; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px;">Product Insights Report</h1>`;

  const data = currentReportData;

  if (data.executive_summary) {
    html += `<h2 style="font-size: 18px; margin-top: 20px; margin-bottom: 10px;">Executive Summary</h2>`;
    html += `<p style="margin-bottom: 8px;"><strong>Overall Problem:</strong> ${data.executive_summary.overall_problem || '—'}</p>`;
    html += `<p style="margin-bottom: 8px;"><strong>Primary Need:</strong> ${data.executive_summary.primary_user_need || '—'}</p>`;
    html += `<p style="margin-bottom: 8px;"><strong>Biggest Opportunity:</strong> ${data.executive_summary.biggest_opportunity || '—'}</p>`;
  }

  if (data.sentiment_analysis) {
    html += `<h2 style="font-size: 18px; margin-top: 20px; margin-bottom: 10px;">Sentiment Analysis</h2>`;
    html += `<p style="margin-bottom: 8px;"><strong>Overall Sentiment:</strong> ${data.sentiment_analysis.overall_sentiment || '—'}</p>`;
  }

  if (data.key_pain_points && data.key_pain_points.length) {
    html += `<h2 style="font-size: 18px; margin-top: 20px; margin-bottom: 10px;">Key Pain Points</h2><ul style="padding-left: 20px; margin-bottom: 10px;">`;
    data.key_pain_points.forEach(p => {
      html += `<li style="margin-bottom: 8px;"><strong>${p.pain_point}</strong> (Freq: ${p.frequency}, Severity: ${p.severity})<br><em>Ex: "${(p.example_reviews && p.example_reviews[0]) || ''}"</em></li>`;
    });
    html += `</ul>`;
  }

  if (data.root_causes && data.root_causes.length) {
    html += `<h2 style="font-size: 18px; margin-top: 20px; margin-bottom: 10px;">Root Causes</h2><ul style="padding-left: 20px; margin-bottom: 10px;">`;
    data.root_causes.forEach(r => html += `<li style="margin-bottom: 8px;"><strong>${r.problem}:</strong> ${r.reasoning}</li>`);
    html += `</ul>`;
  }

  if (data.recommendation_frustrations && data.recommendation_frustrations.length) {
    html += `<h2 style="font-size: 18px; margin-top: 20px; margin-bottom: 10px;">Recommendation Frustrations</h2><ul style="padding-left: 20px; margin-bottom: 10px;">`;
    data.recommendation_frustrations.forEach(f => html += `<li style="margin-bottom: 8px;"><strong>${f.issue}:</strong> ${f.why_it_happens}</li>`);
    html += `</ul>`;
  }

  if (data.desired_listening_behaviors && data.desired_listening_behaviors.length) {
    html += `<h2 style="font-size: 18px; margin-top: 20px; margin-bottom: 10px;">Desired Listening Behaviors</h2><ul style="padding-left: 20px; margin-bottom: 10px;">`;
    data.desired_listening_behaviors.forEach(b => html += `<li style="margin-bottom: 8px;"><strong>${b.behavior}:</strong> ${b.user_goal}</li>`);
    html += `</ul>`;
  }

  if (data.repeat_listening_causes && data.repeat_listening_causes.length) {
    html += `<h2 style="font-size: 18px; margin-top: 20px; margin-bottom: 10px;">Repeat Listening Causes</h2><ul style="padding-left: 20px; margin-bottom: 10px;">`;
    data.repeat_listening_causes.forEach(c => html += `<li style="margin-bottom: 8px;"><strong>${c.cause}:</strong> ${c.evidence}</li>`);
    html += `</ul>`;
  }

  if (data.user_segments && data.user_segments.length) {
    html += `<h2 style="font-size: 18px; margin-top: 20px; margin-bottom: 10px;">User Segments</h2><ul style="padding-left: 20px; margin-bottom: 10px;">`;
    data.user_segments.forEach(s => html += `<li style="margin-bottom: 8px;"><strong>${s.segment}</strong> - ${s.description} (Needs: ${(s.needs || []).join(', ')})</li>`);
    html += `</ul>`;
  }

  if (data.unmet_needs && data.unmet_needs.length) {
    html += `<h2 style="font-size: 18px; margin-top: 20px; margin-bottom: 10px;">Unmet Needs</h2><ul style="padding-left: 20px; margin-bottom: 10px;">`;
    data.unmet_needs.forEach(n => html += `<li style="margin-bottom: 8px;"><strong>${n.need}</strong> (Importance: ${n.importance})</li>`);
    html += `</ul>`;
  }

  if (data.feature_requests && data.feature_requests.length) {
    html += `<h2 style="font-size: 18px; margin-top: 20px; margin-bottom: 10px;">Feature Requests</h2><ul style="padding-left: 20px; margin-bottom: 10px;">`;
    data.feature_requests.forEach(f => html += `<li style="margin-bottom: 8px;"><strong>${f.feature}:</strong> ${f.reason}</li>`);
    html += `</ul>`;
  }

  if (data.strategic_product_insights && data.strategic_product_insights.length) {
    html += `<h2 style="font-size: 18px; margin-top: 20px; margin-bottom: 10px;">Strategic Insights</h2><ul style="padding-left: 20px; margin-bottom: 10px;">`;
    data.strategic_product_insights.forEach(i => html += `<li style="margin-bottom: 8px;"><strong>${i.insight}</strong><br>Impact: ${i.business_impact}</li>`);
    html += `</ul>`;
  }

  if (data.ai_product_opportunities && data.ai_product_opportunities.length) {
    html += `<h2 style="font-size: 18px; margin-top: 20px; margin-bottom: 10px;">AI Product Opportunities</h2><ul style="padding-left: 20px; margin-bottom: 10px;">`;
    data.ai_product_opportunities.forEach(o => html += `<li style="margin-bottom: 8px;"><strong>${o.opportunity}</strong><br>Why AI: ${o.why_ai_is_needed}</li>`);
    html += `</ul>`;
  }

  html += `</div>`;

  const opt = {
    margin: [15, 15, 15, 15],
    filename: `Product_Insights_Report_${new Date().toISOString().slice(0, 10)}.pdf`,
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { scale: 2, useCORS: true, logging: false },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
  };

  html2pdf().set(opt).from(html).save().then(() => {
    els.btnExportPdf.innerHTML = '📄 Export PDF Report';
  });
});

// ─── Event Listeners ───────────────────────────────────────────────────────────
els.textarea.addEventListener('input', () => {
  updateCharCounter();
  if (els.textarea.value.trim()) hideValidation();
});

els.sampleSizeSlider.addEventListener('input', (e) => {
  const val = parseInt(e.target.value, 10);
  els.sampleSizeVal.textContent = val.toLocaleString();

  if (val > 100) {
    els.mapReduceWarning.style.display = 'inline-block';
  } else {
    els.mapReduceWarning.style.display = 'none';
  }
});

els.analyzeDatasetBtn.addEventListener('click', () => {
  if (!isLoading) analyzeDataset();
});

els.loadSampleBtn.addEventListener('click', loadSampleReview);

els.analyzeBtn.addEventListener('click', () => {
  if (!isLoading) analyzeReviews();
});

// Allow Ctrl+Enter to submit
els.textarea.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !isLoading) {
    analyzeReviews();
  }
});

// ─── Init ──────────────────────────────────────────────────────────────────────
updateCharCounter();
