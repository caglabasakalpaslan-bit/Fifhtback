# Fifthback — Product Requirements (living doc)

## Original Problem Statement
Build Fifthback, a privacy-protected corporate feedback resolution system. Employees answer one open question "What's happening?" (no HR forms, no A-vs-B). Optional "express it with a song". An AI worker "Feedback Interpreter" extracts only what the text supports: feedback_type (REQUEST/TENSION/PROBLEM/SUGGESTION/POSITIVE/OTHER), 1-4 signals with exact evidence, and a short pattern candidate — never forcing a dilemma, diagnosing, or inventing meaning. Then "Did we understand you correctly?" confirm/correct. A Manager Dashboard shows aggregated recurring patterns (pattern, frequency, affected teams, time unresolved, blocker, status NEW/ACTIVE/STUCK/RESOLVED), never identities. Human, warm, playful, memorable. Polished 60-second demo. Simple architecture. No auth/payments/integrations/extra agents yet.

## User Choices
- LLM: Claude Sonnet 4.6 (Emergent Universal Key)
- Pre-seed demo patterns: Yes
- Visual vibe: Warm & editorial

## Architecture
- Backend: FastAPI + MongoDB (motor). AI via emergentintegrations LlmChat (anthropic/claude-sonnet-4-6). Deterministic fallback extractor for demo reliability.
  - POST /api/interpret, POST /api/feedback/confirm, GET /api/patterns; seed 5 demo patterns on startup.
- Frontend: React (single page, tab toggle Employee Voice / Manager Lens), Tailwind, framer-motion, lucide-react, sonner. Newsreader serif + Plus Jakarta Sans + JetBrains Mono, warm parchment palette.

## User Personas
- Employee: shares feedback anonymously, confirms interpretation.
- Manager: reviews aggregated anonymized patterns to unblock teams.

## Implemented (2026-06)
- Feedback Interpreter with verbatim-evidence extraction + song note (Claude 4.6, verified real LLM path).
- Confirm / inline-correct flow; confirmed feedback folds into anonymized pattern pool.
- Manager Dashboard: metrics, status filters, pattern cards, privacy guarantee banner.
- Pre-seeded 5 demo patterns; 60-second demo presets one-click.
- Full UI translated to Turkish (all static labels + AI output in Turkish).
- Result redesigned into 5-step "Fifthback Çözüm Yolculuğu": (1) Seni nasıl anladık? (2) Bu örüntü ne kadar yaygın? — real seeded prevalence only, honest empty state (3) Buradaki asıl gerilim ne? — co-active needs, never A/B (4) Kim ne yapabilir? — org vs personal responsibility, no blame (5) Nasıl kapanabilir? — channels with trade-offs + safety note. Actions: Yanlış anlaşılanı düzelt / Bir şey ekle / Böyle gönder.
- Full E2E tested (8/8 backend, all frontend flows pass, iteration_2). Toast overlap fixed via pointer-events.

## Backlog / Next (P1/P2)
- Pattern detail modal deep-dive; near-duplicate pattern merging (fuzzy match).
- Warm dark-mode toggle.
- Manager status editing (advance NEW→ACTIVE→RESOLVED).
- Trend sparkline per pattern over time.
