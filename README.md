# DeployWatch — Backend

AI-powered production readiness agent. Scans GitHub repos, scores them across 6 categories, generates code fixes via Claude, and opens PRs automatically.

## Stack
- **FastAPI** — API server
- **ARQ + Redis** — async job queue
- **Claude API** — generates file-level fixes
- **PyGithub** — opens PRs
- **Prometheus + Grafana** — observability

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # Fill in your keys
```

## Run locally

**Start Redis + everything via Docker Compose:**
```bash
docker-compose up redis
```

**API server:**
```bash
uvicorn main:app --reload
```

**ARQ worker (separate terminal):**
```bash
python -m arq workers.WorkerSettings
```

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/analyze` | Submit repo URL, returns `job_id` |
| GET | `/status/{job_id}` | Poll for result |
| GET | `/health` | Health check |
| GET | `/ready` | Readiness check |
| POST | `/webhook/{repo_id}` | GitHub push webhook |
| GET | `/history/{owner}/{repo}` | Scan history |
| POST | `/loadtest` | Load test a URL |
| GET | `/metrics` | Prometheus metrics |

## Env vars

| Key | Required | Description |
|-----|----------|-------------|
| `ANTHROPIC_API_KEY` | ✅ | Claude API key |
| `GITHUB_TOKEN` | ✅ | For opening PRs |
| `REDIS_URL` | ✅ | Redis connection string |
| `DISCORD_WEBHOOK_URL` | Optional | For score-drop alerts |
| `GITHUB_WEBHOOK_SECRET` | Optional | HMAC secret for webhooks |
| `SCORE_DROP_THRESHOLD` | Optional | Alert if score drops by this much (default: 10) |

## Deploy to Railway

1. Create a Railway project, add a Redis plugin
2. Set all env vars above
3. Deploy — Railway auto-detects the Dockerfile
