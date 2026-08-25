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
- **Reasoning engine deepened (2026-06)**: Added 2nd AI worker **Distinction Questioner** (`/api/distinction`) — after the interpreter, decides if ONE discriminating question would materially change meaning (10 Signal / 20 Active factors / 30 single question); multi-select options + free text + "Hiçbiri"; STOPS when a question adds little. Added **Evaluator** (`/api/evaluate`) — refines the interpretation with the answer and checks whether it is grounded in the employee's actual words (flags assumption-based factors). Integrated as a dynamic journey step (no UI redesign), interpretation.id preserved to avoid remount. No new dashboards/integrations. Verified iteration_3 (100%/100%). NOTE: /interpret ~20-25s, /evaluate ~25-40s (sequential Claude calls) — latency is a known demo consideration.

## Backlog / Next (P1/P2)
- **Pattern Room v2 (2026-06)**: (1) **Add signals** — managers paste anonymous signals (one/line) → appended to a persisted pool (`pattern_room_meta`) → structural mechanism-based re-clustering; new/changed clusters flagged (`is_new`/`changed`) and new signals tagged in the pile. (2) **Click cluster → FF Cam** — highlights supporting signals, dims the rest, and shows a "Neden birlikte?" panel separating direct evidence / AI inference / remaining uncertainty. (3) **Action Board** — move any pattern to a tracking board with states DETECTED/INVESTIGATING/TESTING/RESOLVED/**REJECTED** (falsifiable), storing evidence snapshot, hypothesis, intervention, outcome, created_at/updated_at (history recorded for future trend charts — not built yet). New endpoints: `/pattern-room/signals`, `/pattern-room/add-signals`, `GET/POST/PATCH /action-board`. Live Claude re-cluster with 45s timeout→curated fallback (Cloudflare-safe). Verified iteration_5 = backend 11/11, frontend 100%.
- **Pattern Room (2026-06)**: New 3rd manager view "FIFTHBACK — PATTERN ROOM". 24 anonymous work-system signals clustered by underlying MECHANISM (not keywords) via 3 AI roles in one Claude pass: Cluster Agent, Impact Agent (top-5, qualitative/"tahmini" cost, no invented money), Solution Pattern Agent (past cases + max-3 non-prescriptive "Denemeye değer/Benzer vakalarda/Şu koşulda" moves). Top cluster = Karar Akışı / Sahiplik Darboğazı (decision-flow/ownership bottleneck). LEFT signal pile → CENTER mechanism clusters → RIGHT top-5; click opens FF CAM / Etki / Geçmiş / Hamle dialog. Instant curated analysis seeded at startup + cached in `pattern_room_cache`; "Fif ile yeniden analiz et" runs live Claude with a 60s wall-clock timeout→curated fallback (avoids Cloudflare 100s 502). Not employee scoring — work-system friction only. Verified iteration_4 (backend 8/9 incl. bounded-timeout, frontend 100%).
- Pattern detail modal deep-dive; near-duplicate pattern merging (fuzzy match).
- Warm dark-mode toggle.
- Manager status editing (advance NEW→ACTIVE→RESOLVED).
- Trend sparkline per pattern over time.
