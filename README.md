# Fifthback

**ANLAT — "Burası sesinin duyulduğu yer."**

A person tells a story (typed or spoken). The Fifth Core asks at most one genuinely useful
question, then returns a Fifth Card: AYRIM · NEDEN ÖNEMLİ · HÂLÂ AÇIK · YANINDA GÖTÜR.
Finished cards are kept in the user's browser under **Kartlarım**. No account, no profile.

## Stack

- `backend/` — FastAPI + MongoDB (motor). The core is one direct call to the Anthropic Messages API
  (`claude-sonnet-4-6`, streamed). No agent framework, no fallback output: if the model cannot be
  reached the API answers `503 model_unavailable` and the UI says so.
- `frontend/` — React (CRA + craco), react-router, Tailwind. Public routes: `/`, `/anlat`,
  `/anlat/:sessionId`, `/kartlarim`. Everything else redirects to `/`.

## Configuration (Emergent)

`backend/.env`

```
MONGO_URL=...            # provided by the platform
DB_NAME=...              # provided by the platform
FIFTHBACK_ANTHROPIC_KEY=...  # your paid Anthropic key — REQUIRED for the core to work
ANTHROPIC_API_KEY=...        # accepted as a fallback name for the same key
```

`frontend/.env`

```
REACT_APP_BACKEND_URL=...   # provided by the platform
```

Credential resolution in the core, in order: `FIFTHBACK_ANTHROPIC_KEY` → `ANTHROPIC_API_KEY` (both direct
connection) → an egress
credential proxy (`HTTPS_PROXY`, sandbox runtimes only) → honest unavailable. The key is never
logged or returned by any endpoint. `GET /api/fifth/status` reports only the credential *mode*.

## What is in the codebase but not in the public product

- KENDİNİ BUL (`frontend/src/pages/Kesfet.js`): structural shell, announced on the landing page as
  "yakında", not routed.
- Legacy internal views (`Internal.js`, `EmployeeVoice`, `ManagerDashboard`, `PatternRoom`,
  `FifthCore`) and their `/api/interpret`-style endpoints: not routed from the UI.
- Reveal enrichment (LIBRARIAN → SKEPTIC → STORYTELLER, `backend/fifth_roles/`, Olympus content in
  `backend/olympus/`): endpoint `POST /api/fifth/enrich/{session_id}` exists, the UI does not call it.
- Evaluation tooling: `backend/eval/` (baseline stories, runners, results).

## Tests

```
cd backend && python -m pytest tests/test_tournament_routing.py tests/test_fifth_roles.py -q   # no network
REACT_APP_BACKEND_URL=http://localhost:8001 python -m pytest tests/test_fifth_core.py -q       # real API
```
