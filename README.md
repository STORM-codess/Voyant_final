# Voyant ✦ AI-Powered Group Travel Planning

> Picked by your group, decided by a vote. Voyant helps friends plan a trip together — everyone shares their preferences, an AI recommendation engine proposes destinations that fit the *whole group*, and a ranked-choice vote settles where you go.

---

## Why this project exists

Planning a group trip is a coordination problem: everyone has different budgets, vibes, and dates, and group chats rarely converge on a decision. Voyant turns that into a structured flow — collect everyone's preferences, let an AI weigh the *shared* signals, and resolve the choice with a fair vote.

It was built as a portfolio project with a focus on **real engineering depth over surface features**: a resilient multi-model AI gateway, versioned prompts with automated evaluation, full observability, and an honest "no fake data, no dead buttons" build philosophy.

---

## How it works

```
Create trip  →  Invite friends (share link)  →  Everyone fills a preferences form
      →  AI generates destination recommendations  →  Group votes (instant-runoff)  →  Plan is shared
```

1. **Create a trip** — name it; destination and dates are intentionally left open ("the group decides later").
2. **Invite friends** — share a join link; anyone who opens it can sign in and join.
3. **Collect preferences** — members fill a form (budget, trip length, vibe, route preference, exclusions, and more). Admins can pick from templates or build a custom question set.
4. **Generate recommendations** — the AI aggregates every member's answers and proposes destinations (single-base *or* multi-city routes) sized to the trip, each with reasoning, suggested activities, budget ranges, and a match score.
5. **Vote** — the group ranks their choices; an instant-runoff tally (with tie → revote → random-tiebreak handling) produces a fair winner.
6. **Itineraries** — generate a day-by-day plan for any recommendation on demand.

---

## Engineering highlights

This is the part worth reading — the AI layer is built like a production system, not a thin API wrapper.

### Resilient model gateway with fallback
AI calls route through a gateway with an automatic fallback chain: **Llama 3.1 8B (primary) → Llama 3.3 70B → Gemini Flash**. If a provider fails or rate-limits, the request rolls to the next model so the feature never goes down. The primary was chosen by *matching model capability to task difficulty* — structured destination JSON isn't a frontier-reasoning task, so the cheapest/fastest model that clears the quality bar wins, with stronger models held in reserve.

### Versioned prompts + offline evaluation
Prompts are **versioned** (e.g. `recommendations_v1/v2/v3`), never overwritten, so prompt iterations form an auditable history. Every AI response is scored against **deterministic quality checks** (valid JSON, correct count, required fields, no duplicates, respects the group's exclusions) producing a 0–1 eval score — no "LLM judging an LLM." This enables honest offline prompt benchmarking: which version scores higher, at what cost.

### Full observability
Every AI call is logged to a dedicated table with its model, prompt version, token counts, estimated cost, latency, success/fallback position, and eval score. These aggregates power a public **["How our AI works"](https://voyant-eta.vercel.app/how-ai)** showcase page — all numbers are real telemetry, not hardcoded.

### Other notable bits
- **Instant-runoff voting** with tie detection, automatic revote, and random tiebreak.
- **Multi-city route recommendations** — an option can be a single base or a sized A→B→C route.
- **Link-based invites** — share a trip link; opening it lets anyone sign in and join (no email infrastructure required).
- **Connection resilience** — `pool_pre_ping` + `pool_recycle` handle serverless Postgres dropping idle connections.

---

## Tech stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) (async) + [Uvicorn](https://www.uvicorn.org/)
- [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (async) over [Neon](https://neon.tech/) serverless Postgres (`asyncpg`)
- [Firebase Admin](https://firebase.google.com/docs/admin/setup) for auth (Firebase UID = user primary key)
- AI: [Groq](https://groq.com/) (Llama models) + [Google Gemini](https://ai.google.dev/), behind a custom gateway
- `slowapi` (rate limiting), `prometheus-fastapi-instrumentator` (metrics), `httpx` (transactional email via [Resend](https://resend.com/))

**Frontend**
- [React](https://react.dev/) + [Vite](https://vitejs.dev/)
- [Firebase Auth](https://firebase.google.com/docs/auth) (Google sign-in)
- `react-router-dom`, `lucide-react` icons
- Inline styles (no CSS framework), custom cinematic hero with a card-to-background shared-element transition

---

## Architecture

```
┌─────────────────┐         ┌──────────────────────────┐         ┌─────────────────┐
│  React + Vite   │  HTTPS  │   FastAPI backend        │         │  Neon Postgres  │
│  (Vercel)       │ ──────► │   (Render)               │ ──────► │  (serverless)   │
│                 │         │                          │         └─────────────────┘
│  Firebase Auth  │         │  ┌────────────────────┐  │
│  (Google login) │         │  │  AI Model Gateway  │  │  ┌──────────────────────┐
└─────────────────┘         │  │  Llama → Llama →   │ ─┼─►│ Groq / Gemini APIs   │
                            │  │  Gemini (fallback) │  │  └──────────────────────┘
        ▲                   │  └────────────────────┘  │
        │  ID token         │  eval harness + ai_calls │
        └───────────────────┤  observability table     │
                            └──────────────────────────┘
```

The frontend authenticates with Firebase, then sends the Firebase ID token as a Bearer header on every request. The backend verifies the token via Firebase Admin and uses the Firebase UID as the user identity throughout.

---

## Running locally

### Prerequisites
- Python 3.11+ and Node 18+
- A Neon (or any Postgres) database URL
- A Firebase project (for Google auth) + service-account JSON
- A Groq API key (and optionally a Gemini key)

### Backend
```bash
cd Backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

Create `Backend/.env`:
```env
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
SECRET_KEY=a_real_random_secret
CORS_ORIGINS=http://localhost:5173
# Firebase service-account JSON — as a file locally, or FIREBASE_CREDENTIALS env var in prod
```
Place your Firebase service-account file at `Backend/firebase_credentials.json` (gitignored).

Run:
```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
API docs are auto-generated at `http://localhost:8000/docs`.

### Frontend
```bash
cd Frontend
npm install
```
Set your Firebase web config in `src/firebase.js`, then create `Frontend/.env` (optional for local):
```env
VITE_API_BASE=http://localhost:8000
```
Run:
```bash
npm run dev
```

---

## Deployment

| Layer | Host | Key config |
|-------|------|-----------|
| Frontend | Vercel | `VITE_API_BASE` → backend URL; SPA rewrite in `vercel.json` |
| Backend | Render | `DATABASE_URL`, `GROQ_API_KEY`, `SECRET_KEY`, `CORS_ORIGINS` → frontend URL, `FIREBASE_CREDENTIALS` (JSON as env var) |
| Database | Neon | serverless Postgres; schema built via SQLAlchemy `create_all` on startup |
| Auth | Firebase | deployed domain added to **Authorized domains** |

Notes from real deployment:
- Firebase service-account credentials are loaded from the `FIREBASE_CREDENTIALS` env var in production (the JSON file is gitignored and never deployed).
- Transactional email uses Resend's **HTTP API** rather than SMTP, since most cloud hosts block outbound SMTP ports.
- `CORS_ORIGINS` must list the exact frontend origin with **no trailing slash**.

---

## Project structure

```
Backend/
├── main.py                  # app entry: routers, CORS, rate limiting, startup
├── app/
│   ├── api/                 # route handlers (trips, forms, recommendations, votes, ai_metrics, …)
│   ├── models/              # SQLAlchemy models (trip, user, form, vote, recommendation, ai_call, …)
│   ├── services/            # model_gateway, ai_service, prompts, eval, email, template_seeder
│   ├── firebase.py          # Firebase Admin auth dependency
│   ├── config.py            # settings (env-driven)
│   └── database.py          # async engine + session
└── requirements.txt

Frontend/
├── src/
│   ├── VoyantHero.jsx       # cinematic landing hero
│   ├── VoyantDashboard.jsx  # trips dashboard
│   ├── VoyantTripDetail.jsx # overview / form / recommendations / vote tabs
│   ├── VoyantHowAI.jsx      # public AI-engineering showcase
│   ├── FormTab.jsx, VotePanel.jsx, …
│   ├── AuthContext.jsx      # Firebase auth + backend user sync
│   └── api.js               # fetch wrapper with Bearer token
└── vercel.json
```

---

## Design philosophy

- **No fake data, no dead buttons.** Every metric shown is real telemetry; every button does something.
- **Honesty over decoration.** The AI showcase describes what's actually built (offline eval, deliberately exercised fallback) rather than overselling.
- **Real engineering narrative.** Choices (why an 8B primary model, why offline eval vs. live A/B, link-based invites over SMTP) are made deliberately and explained.

---

## Status & roadmap

Voyant is feature-complete for its core loop and deployed. Possible next steps:
- Verified email domain for transactional invites to any recipient (currently link-based)
- Mobile-responsive polish
- Plan export / sharing

---

## License

This project is for portfolio and educational purposes.

---

<p align="center"><em>Built with care — a space to plan, not just a wrapper around an API.</em></p>
