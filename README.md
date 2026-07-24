# INGRES-AI Backend

Backend for **INGRES-AI** (SIH25066, Ministry of Jal Shakti) — a conversational
assistant over CGWB/INGRES groundwater data. It takes a user's message,
retrieves matching groundwater records from the **National Water Data Portal**
(or a bundled reference dataset), feeds that data to an **AI model** as
grounding context, and returns a structured JSON response your frontend can
render as chat text, a chart, and/or a table.

No PostgreSQL, no ORM, no migrations — data comes straight from an API/JSON
layer as requested. Everything is async FastAPI + `httpx`.

---

## 1. How a request flows through the system

```
Frontend (React)
      │  POST /api/v1/chat  { message, session_id }
      ▼
┌──────────────────────────────────────────────────────────────┐
│ FastAPI (app/main.py)  — CORS-enabled                        │
│                                                                │
│  1. routers/chat.py                                           │
│       │                                                       │
│       ├─ services/nlu.py            → intent + state/district │
│       │                                                       │
│       ├─ services/water_data_service.py                       │
│       │     ├─ USE_LIVE_WATER_API=true  → National Water      │
│       │     │    Data Portal (data.gov.in-style, api-key)     │
│       │     └─ else / on failure        → local reference     │
│       │          dataset (app/data/mock_groundwater.json)     │
│       │                                                       │
│       ├─ services/crop_advisory.py  → advisory bullets         │
│       │                                                       │
│       ├─ services/llm_service.py                              │
│       │     └─ AI model API (Groq, key from .env) with the    │
│       │        retrieved data as context → generated reply    │
│       │        (falls back to a direct data summary if the    │
│       │         model call fails — never a dead end)          │
│       │                                                       │
│       └─ services/memory.py          → in-memory session log   │
└──────────────────────────────────────────────────────────────┘
      ▼
{ reply, records, chart, crop_advisory, session_id, ... }
```

---

## 2. What's implemented vs. the proposal's four pillars

Built to be honest about scope: a fully working chat + data backend, with
lightweight (not heavyweight-ML) versions of pillars 3 and 4. Pillars 1 and 2
are documented extension points rather than faked.

| Pillar | Proposal | This backend |
|---|---|---|
| Core | Text-to-SQL/GIS agent over PostgreSQL+PostGIS | Query over an API-backed dataset (no DB, per your request) — state/district filtering, not free-form SQL |
| 1. GIS Agent | Maps via Leaflet/Mapbox in-chat | Not built — each record includes `latitude`/`longitude` so a map component can plot them; rendering the map is a frontend job |
| 2. Bhashini Voice | Vernacular STT/TTS | Not built — `ChatRequest.language` is a reserved hook to route to Bhashini later |
| 3. Predictive Recharge | LSTM/Prophet forecasting | Lightweight linear-trend projection (`/forecast`), clearly labeled as a placeholder for a real model |
| 4. Crop Advisory | Auto farming counsel | Fully working rule-based lookup, blended into the LLM's answer |

See **§8** for how to extend the two "not built" items.

---

## 3. Project structure

```
ingres-ai-backend/
├── app/
│   ├── main.py                    # FastAPI app + CORS
│   ├── config.py                  # All settings & API keys (from .env)
│   ├── schemas.py                 # Request/response models
│   ├── routers/
│   │   ├── chat.py                 # POST /api/v1/chat, /api/v1/chat/reset
│   │   └── groundwater.py          # /states /districts /status /categories /forecast
│   ├── services/
│   │   ├── llm_service.py          # Calls the AI model, returns the reply
│   │   ├── water_data_service.py   # National Water Data Portal client + fallback
│   │   ├── nlu.py                  # Intent + location extraction
│   │   ├── crop_advisory.py        # Category → farming guidance lookup
│   │   ├── forecast.py             # Simple trend projection
│   │   └── memory.py               # In-memory conversation history
│   └── data/mock_groundwater.json # Reference dataset (21 blocks × 5 years)
├── scripts/
│   ├── generate_mock_data.py      # Regenerates the reference dataset
│   └── smoke_test.sh              # One-command endpoint check
├── requirements.txt
├── .env.example                   # Copy to .env and fill in
├── run.sh                         # Setup + run in one command
└── .gitignore
```

---

## 4. Step-by-step setup

### Step 1 — Prerequisites
- Python 3.10+
- A free [Groq](https://console.groq.com/keys) account for the AI model API key (recommended — matches the proposal's Llama/Groq stack and has a generous free tier)
- Optionally, a free [data.gov.in](https://data.gov.in) or [India-WRIS](https://indiawris.gov.in) account if you want *live* groundwater data later (the app runs fully without this — see §6)

### Step 2 — Fastest path: one command
```bash
cd ingres-ai-backend
./run.sh
```
This creates a virtualenv, installs dependencies, creates `.env` from
`.env.example` on first run, and starts the server at `http://localhost:8000`.
Skip to Step 5.

### Step 2 (alternative) — Manual setup
```bash
cd ingres-ai-backend
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3 — Configure environment
```bash
cp .env.example .env
```
Open `.env` and set at minimum:
```
GROQ_API_KEY=your_real_groq_key_here
```
Everything else already has a working default (see the comments in
`.env.example` for what each value means). **Never commit your real `.env`** —
it's already in `.gitignore`.

### Step 4 — Run the server
```bash
uvicorn app.main:app --reload --port 8000
```
You should see `Application startup complete`. Leave this running.

### Step 5 — Verify it's alive
```bash
curl http://localhost:8000/health
```
This reports whether the LLM key is configured and whether you're in live or
reference-dataset mode — useful for debugging without printing the actual
key. Interactive API docs (Swagger UI) are at **http://localhost:8000/docs** —
open that in a browser to try every endpoint by hand.

Or run everything at once:
```bash
./scripts/smoke_test.sh
```
This fires every endpoint (health, groundwater data, chat, CORS preflight)
and prints the responses — the same checks used while building this.

### Step 6 — Talk to it
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the groundwater status in Wardha?"}'
```
This works immediately, even before you add a real Groq key — you'll get a
direct data summary instead of an LLM-generated reply, with
`"llm_status": "offline_fallback (...)"` telling you why. Add your Groq key
and re-run the same command to see the AI-generated version.

---

## 5. API reference

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Service + config status (no secrets exposed) |
| POST | `/api/v1/chat` | Main assistant endpoint. Body: `{message, session_id?, language?}` |
| POST | `/api/v1/chat/reset?session_id=...` | Clears a session's conversation history |
| GET | `/api/v1/groundwater/states` | List of states in the current dataset |
| GET | `/api/v1/groundwater/districts?state=...` | Districts for a state |
| GET | `/api/v1/groundwater/status/{state}?district=&block=` | Latest structured records + category summary |
| GET | `/api/v1/groundwater/categories?state=` | Safe/Semi-Critical/Critical/Over-Exploited/Saline counts |
| GET | `/api/v1/groundwater/forecast/{state}?district=&block=` | Historical trend + next-year projection |

`ChatResponse` shape (see `app/schemas.py` for the full definition):
```json
{
  "session_id": "uuid",
  "reply": "text for the chat bubble",
  "intent": "status | forecast | advisory | list_critical | compare | greeting | help | general",
  "entities": { "state": "...", "district": "..." },
  "records": [ { "state": "...", "category": "Over-Exploited", "...": "..." } ],
  "chart": { "type": "pie|line", "title": "...", "labels": [...], "values": [...] },
  "crop_advisory": ["...", "..."],
  "data_source": "local_reference_dataset | national_water_data_portal_live",
  "llm_status": "ok | offline_fallback (...)",
  "generated_at": "2026-07-23T..."
}
```

---

## 6. Connecting your frontend

CORS is already enabled in `app/main.py` via `FRONTEND_ORIGINS` in `.env`.
Add your dev URL and your deployed URL (comma-separated, no spaces), e.g.:
```
FRONTEND_ORIGINS=http://localhost:3000,http://127.0.0.1:5173,https://your-deployed-frontend.vercel.app
```

Minimal fetch example from your existing frontend:
```javascript
async function sendMessage(message, sessionId) {
  const res = await fetch("http://localhost:8000/api/v1/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`Chat request failed: ${res.status}`);
  return res.json(); // { reply, records, chart, crop_advisory, session_id, ... }
}

// Keep the returned session_id and pass it back on every subsequent call
// so the assistant remembers the last few turns.
```
- Render `reply` as the assistant's chat bubble.
- Feed `chart` straight into a recharts/Chart.js component — `labels`/`values` are already shaped for bar/pie/line.
- `records` has per-block rows including `latitude`/`longitude` for a table or map.

If your frontend already has its own request/response field names, the
easiest path is adjusting the fetch call above to match — the contract lives
entirely in `app/schemas.py` and `app/routers/chat.py`, so tell me what your
frontend currently sends/expects and I can adjust these precisely instead of
you reshaping the frontend.

---

## 7. Moving from sample data to the live National Water Data Portal

By default `USE_LIVE_WATER_API=false`, so every request is served from
`app/data/mock_groundwater.json` — realistic sample data modeled on real CGWB
assessment categories (Safe/Semi-Critical/Critical/Over-Exploited/Saline),
**not official figures**. To go live:

1. Register at [data.gov.in](https://data.gov.in) (or [indiawris.gov.in](https://indiawris.gov.in)) and get your own API key.
2. Find the resource ID for the groundwater dataset you want (their catalog search, or India-WRIS's data section).
3. In `.env`, set:
   ```
   WATER_DATA_API_KEY=your_real_key
   WATER_DATA_RESOURCE_ID=the_resource_uuid
   USE_LIVE_WATER_API=true
   ```
4. Restart the server. `water_data_service.py` calls the live endpoint first
   and only falls back to the local dataset if that call fails — so a flaky
   connection during a demo never breaks the assistant.

The `WATER_DATA_API_KEY` shipped in `.env.example`
(`579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b`) is data.gov.in's
own **publicly published sample key** from their API documentation, meant for
trying endpoints before registering — treat it as a placeholder, not a
private credential, and get your own key for anything beyond quick testing.

---

## 8. Changing the AI model / provider, and extending toward the full proposal

`llm_service.py` calls Groq's Chat Completions endpoint, which is
OpenAI-wire-compatible. Three env vars control it entirely:
```
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_API_KEY=...
GROQ_MODEL=openai/gpt-oss-20b
```
**A note on model choice:** Groq's docs (checked directly while building
this) show `llama-3.1-8b-instant` and `llama-3.3-70b-versatile` — what the
original proposal names — were deprecated on 2026-06-17 with a shutdown date
of **2026-08-16**. They still work today but will stop shortly, so this
defaults to their recommended replacement, `openai/gpt-oss-20b` (fast,
cheap). For higher-quality answers at the cost of a bit more latency, switch
to `openai/gpt-oss-120b`. To use a different provider entirely (OpenAI
directly, OpenRouter, Together AI, a local Ollama server), just point
`GROQ_BASE_URL` at that provider's OpenAI-compatible endpoint — nothing else
in the codebase needs to change.

**Extending the two pillars not built here:**
- **GIS map (Pillar 1):** every record already has `latitude`/`longitude` —
  feed matched records into a Leaflet/Mapbox GL layer on the frontend,
  colored by `category`.
- **Bhashini voice (Pillar 2):** `ChatRequest.language` is already accepted
  and threaded through — add a Bhashini STT call before `/chat` (transcribe →
  send as `message`) and a TTS call after (speak `reply`).
- **A trained forecasting model (Pillar 3):** `forecast.py` is isolated
  specifically so a Prophet/LSTM model can replace the linear fit without
  touching the router or response shape.
- **Scaling per your proposal's own "Scaling Beyond the Hackathon" section**
  (IoT telemetry, WhatsApp/Telegram bot, satellite inputs): all plug in as
  additional data sources behind `water_data_service.get_groundwater_data()`
  — that function is the single seam between "where data comes from" and
  "everything else."

---

## 9. Troubleshooting

- **`ModuleNotFoundError` on startup** → you're not in the virtualenv; run `source .venv/bin/activate` again (or re-run `./run.sh`).
- **CORS error in the browser console** → your frontend's exact origin (protocol + host + port) isn't in `FRONTEND_ORIGINS` in `.env`. Restart the server after editing `.env`.
- **`llm_status` always says `offline_fallback`** → check `/health` — `llm_configured` is `false` if `GROQ_API_KEY` is empty; if a key is set, check the server logs for the specific error (invalid key, network/firewall block to `api.groq.com`, etc.).
- **Live water data never used even with `USE_LIVE_WATER_API=true`** → check `WATER_DATA_RESOURCE_ID` isn't still the placeholder, and check the server logs — failures fall back silently by design, but they're logged.
- **`/api/v1/groundwater/status/{state}` returns 404** → the state name doesn't match the dataset; call `/api/v1/groundwater/states` for the exact supported list.
- **Want more states/districts in the sample data** → edit the `BLOCKS` list in `scripts/generate_mock_data.py` and re-run it; it regenerates `mock_groundwater.json` deterministically.
