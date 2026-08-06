<img width="1366" height="768" alt="INGRES_scrrenshot" src="https://github.com/user-attachments/assets/a72b035d-599f-490f-81fe-e5a86a7fe541" />
# INGRES-AI Backend

Backend for **INGRES-AI** (SIH25066, Ministry of Jal Shakti) — a conversational
assistant over CGWB/INGRES groundwater data. It takes a user's message,
retrieves matching groundwater records from the **National Water Data Portal**
(or a bundled reference dataset),

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
