# backend — AptivCare Assistant

FastAPI service that hosts the REST API, mints LiveKit room tokens, and runs the realtime voice agent (OpenAI STT → OpenAI LLM → OpenAI TTS) against a SQLite store.

## Prerequisites

- Python 3.11 or later.
- A LiveKit Cloud project (free tier is fine) with API key + secret.
- An OpenAI API key.

## Setup

```bash
# from the project root
cd backend

python -m venv .venv
. .venv/Scripts/activate          # PowerShell: .\.venv\Scripts\Activate.ps1
                                   # bash/zsh:  source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env              # fill in real keys; never commit them
```

## How to get each API key

| Variable                | Where                                            |
|-------------------------|--------------------------------------------------|
| `LIVEKIT_API_KEY`       | https://cloud.livekit.io → Project → Settings    |
| `LIVEKIT_API_SECRET`    | same screen as above                             |
| `LIVEKIT_URL`           | the `wss://` URL shown for your project          |
| `OPENAI_API_KEY`        | https://platform.openai.com/api-keys             |
| `OPENAI_LLM_MODEL`      | OpenAI chat model (default: `gpt-4o-mini`)       |
| `OPENAI_STT_MODEL`      | OpenAI speech-to-text model (default: `whisper-1`)|
| `OPENAI_TTS_MODEL`      | OpenAI text-to-speech model (default: `tts-1`)    |
| `OPENAI_TTS_VOICE`      | OpenAI voice (default: `alloy`)                   |
| `OPENAI_SUMMARY_MODEL`  | OpenAI model for post-call summaries              |

`ALLOWED_SLOTS` is a JSON object whose `slots` array lists 24-hour `HH:MM` times the clinic offers each day. The default mirrors a typical 9–6 schedule with a lunch break.

## Run in dev

```bash
python main.py
```

Listens on `http://localhost:8000`. The LiveKit voice-agent worker is launched as a background asyncio task in the same process.

**Working directory:** Secrets are read from **`backend/.env`** next to `config.py`, even if you start Uvicorn from the **repo root** (for example `uvicorn main:app --app-dir backend`). You no longer need `cd backend` just for the env file to load — but `cd backend` is still fine.

`GET /api/health` returns 200 once the DB is open and migrations have run.

## Run the agent worker standalone (optional, production)

If you'd rather run HTTP and the agent on separate machines (recommended at scale), keep the FastAPI process up and run a fleet of dedicated workers:

```bash
python -m agent.voice_agent dev      # dev mode with live reload
python -m agent.voice_agent start    # production mode
```

The standalone worker reads the same `.env` and connects to the same SQLite file.

## Deploy to Railway

1. Create a new Railway project and add a service from your GitHub repo, root path `backend/`.
2. Set every variable from `.env.example` in the Railway dashboard.
3. Add a persistent volume mounted at `/app/data` and set `DATABASE_PATH=/app/data/mykare.db`.
4. Start command: `python main.py`. Healthcheck: `GET /api/health`.

## Architecture

```
                      +------------------+
HTTP requests   -->   |   FastAPI app    |
                      |  /api/* routes   |
                      +---------+--------+
                                |
                +---------------+----------------+
                |                                |
        SQLite (aiosqlite)                LiveKit Worker
        users / appts                     ┌──────────────┐
        sessions                          │ OpenAI STT   │
                                          │ OpenAI LLM   │
                                          │ OpenAI TTS   │
                                          │ Tool registry│
                                          └──────────────┘
```

## Project layout

```
backend/
├── main.py
├── config.py
├── requirements.txt
├── .env / .env.example / .gitignore
├── database/
│   ├── connection.py
│   ├── migrations.py
│   └── models.py
├── agent/
│   ├── voice_agent.py
│   ├── llm_client.py
│   ├── system_prompt.py
│   ├── state.py
│   └── tools/
│       ├── identify_user.py
│       ├── fetch_slots.py
│       ├── book_appointment.py
│       ├── retrieve_appointments.py
│       ├── cancel_appointment.py
│       ├── modify_appointment.py
│       ├── end_conversation.py
│       └── registry.py
├── api/
│   ├── router.py
│   ├── sessions.py
│   ├── summary.py
│   ├── appointments.py
│   └── health.py
└── utils/
    ├── logger.py
    └── rate_limiter.py
```

## Tests / sanity checks

A couple of useful one-liners for local verification:

```bash
# scan for accidentally-hardcoded secrets
rg -n 'sk-[A-Za-z0-9]{20,}|api_key=\"' backend

# create a session and inspect the response
curl -s -X POST http://localhost:8000/api/sessions | jq

# trigger a 429 by hammering it
for i in $(seq 1 20); do curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/sessions; done
```
