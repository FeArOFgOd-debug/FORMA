# Forma

**Research before you build.** Forma turns a short startup idea into a structured market research report: web search, social sentiment (Reddit & X), AI synthesis, competitor context, an idea scorecard, flowchart, revenue sliders, and follow-up chat—backed by a FastAPI pipeline and Convex for jobs and stored results.

## Features

- Live **web research** (Exa) and **social scraping** (Apify) with **sentiment** analysis
- **Business analysis**: score, verdict, SWOT, competitors, risks, recommendations
- **Idea scorecard** (radar chart) and **Mermaid** business-model flowchart
- **Revenue simulation** with adjustable sliders
- **Ask the AI** chat grounded in the generated report
- **PDF export** and progress/ETA during analysis

## Stack

| Layer | Technology |
|--------|------------|
| Frontend | HTML, CSS, JavaScript (static) |
| API | [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/) |
| Data / jobs | [Convex](https://www.convex.dev/) |
| AI | OpenAI (GPT-4o / GPT-4o-mini) |
| Search | [Exa](https://exa.ai/) |
| Social | [Apify](https://apify.com/) |

## Prerequisites

- **Python 3.10+** (recommended)
- **Node.js** (for Convex CLI, if you use Convex locally)
- Accounts / API keys: **OpenAI**, **Convex**, **Exa**, **Apify**

## Environment variables

Create a `.env` file in the **project root** (same folder as `backend/`):

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI API access |
| `CONVEX_URL` | Convex deployment URL (HTTP API) |
| `EXA_API_KEY` | Exa web search |
| `APIFY_API_KEY` | Apify actors (Reddit / X) |

Never commit `.env` to version control.

## Local development

### 1. Backend

```bash
cd /path/to/Hackathon\ Cursor
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.api:app --reload --port 8000
```

API base: `http://127.0.0.1:8000` — try `GET /health`.

### 2. Frontend

Serve the `frontend/` folder (not the repo root):

```bash
cd frontend
python3 -m http.server 3000
```

Open **http://localhost:3000**. The app uses `http://localhost:8000` for the API when the hostname is `localhost` or `127.0.0.1` (see `frontend/app.js`).

### 3. Convex

From the project root, link and deploy Convex per [Convex docs](https://docs.convex.dev/):

```bash
npx convex dev    # development
npx convex deploy # production
```

Ensure `CONVEX_URL` in `.env` matches your deployment.

## Production deployment

- Deploy the **FastAPI** app on a host that supports **long-running requests** (e.g. Railway, Render, Fly.io) with the same environment variables as `.env`.
- Deploy the **static** `frontend/` to Vercel, Netlify, or similar.
- Set the production **API URL** in `frontend/app.js` (`API_BASE`) for non-localhost origins, or use your chosen pattern (env injection, separate config).

## API overview

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/analyze` | Start analysis (`{ "idea": "..." }`) → `job_id` |
| `GET` | `/jobs/{job_id}` | Poll job status + result when complete |
| `POST` | `/chat` | Follow-up chat about a completed report |
| `POST` | `/simulate/revenue` | Revenue simulation |
| `GET` | `/export/{job_id}/pdf` | Download PDF |
| `GET` | `/health` | Health check |

## Project layout

```
├── backend/           # FastAPI app, pipeline, Convex client
├── convex/            # Convex functions (jobs, analyses)
├── frontend/          # Static site (index.html, app.js, index.css)
├── requirements.txt   # Python dependencies
└── .env               # Local secrets (not committed)
```

## License

See [LICENSE.md](LICENSE.md).
