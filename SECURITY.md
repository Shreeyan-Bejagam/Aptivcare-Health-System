# Security

## Secrets

- **Never commit** `backend/.env`, `frontend/.env`, or any file containing API keys, JWT secrets, or database dumps with real patient data.
- Copy `backend/.env.example` → `backend/.env` and `frontend/.env.example` → `frontend/.env` locally only.
- If a key was ever shared in a ticket, chat, or public repo, **rotate it** in LiveKit, OpenAI, Deepgram, and Cartesia dashboards immediately.

## Repository hygiene

- `.gitignore` excludes `.env*`, local SQLite files (`backend/data/*.db*`), `node_modules/`, Python virtualenvs, and build output.
- Do not push production databases or logs containing phone numbers or transcripts.

## Reporting

If you discover a vulnerability, open a private security advisory with the repository maintainers instead of a public issue.
