# frontend — AptivCare Assistant

Vite + React + Tailwind UI for the AptivCare voice agent. Renders the landing page, the live call screen (transcript / avatar / tool feed), and the post-call summary.

## Prerequisites

- Node.js 20 LTS or later.
- The backend (`../backend`) running and reachable at `VITE_API_URL`.

## Setup

```bash
cd frontend
npm install
cp .env.example .env
```

`.env` defaults are correct for local dev:

```
VITE_API_URL=http://localhost:8000
VITE_TAVUS_EMBED_URL=        # optional — Tavus iframe/embed URL (highest priority avatar)
VITE_TAVUS_FACE_VIDEO_URL=   # optional — camera-free Tavus face video for Aria panel
VITE_SIMLI_API_KEY=          # optional — leave blank for SVG fallback avatar
VITE_SIMLI_FACE_ID=          # optional — Simli faceId, only required if a key is set
```

Avatar selection priority:

1. `VITE_TAVUS_FACE_VIDEO_URL` (camera-free Tavus face video)
2. `VITE_TAVUS_EMBED_URL` (Tavus iframe)
3. `VITE_BEYOND_PRESENCE_EMBED_URL` (if configured)
4. Simli (`VITE_SIMLI_API_KEY` + `VITE_SIMLI_FACE_ID`)
5. Built-in animated fallback avatar

The frontend never reads any third-party API key besides Simli. All calls to LLM/STT/TTS providers happen on the backend.

## Run in dev

```bash
npm run dev
```

Opens on `http://localhost:5173`.

## Build for production

```bash
npm run build
npm run preview   # smoke-test the production bundle locally
```

`dist/` is the static output you ship to Vercel / Netlify / S3.

## Routes

| Path             | Component                  | Purpose                            |
|------------------|----------------------------|------------------------------------|
| `/`              | `pages/HomePage.jsx`       | Landing page + start-call CTA      |
| `/call`          | `pages/CallPage.jsx`       | Live call: transcript / avatar / tools |
| `/summary/:id`   | `pages/SummaryPage.jsx`    | Post-call summary, polled until ready |

## Project layout

```
frontend/
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
├── .env / .env.example / .gitignore
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── index.css
    ├── lib/
    │   ├── api.js        # axios client + interceptors (no third-party keys)
    │   └── store.js      # Zustand store (session/transcript/toolEvents/summary/user)
    ├── pages/
    │   ├── HomePage.jsx
    │   ├── CallPage.jsx
    │   └── SummaryPage.jsx
    └── components/
        ├── Avatar.jsx       # Simli + SVG waveform fallback
        ├── CallControls.jsx
        ├── ToolFeed.jsx
        ├── TranscriptView.jsx
        ├── SummaryCard.jsx
        └── Toast.jsx
```

## Deploy to Vercel

1. New project → import the repo, root directory `frontend/`.
2. Build command: `npm run build`. Output directory: `dist`.
3. Environment variables: `VITE_API_URL=https://<your-backend-domain>` (and optionally Simli vars).
4. Vercel handles SPA fallback automatically; no extra config needed.
