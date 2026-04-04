import os
import json
import hmac
import hashlib
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import redis.asyncio as aioredis
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge

# ── Prometheus metrics ────────────────────────────────────────────
pr_opened_total = Counter("deploywatch_pr_opened_total", "Total PRs opened by the agent")
analysis_duration = Histogram("deploywatch_analysis_duration_seconds", "Time for full analysis pipeline")
job_queue_depth = Gauge("deploywatch_job_queue_depth", "Current number of queued/running jobs")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
DB_PATH = "deploywatch.db"

# ── App lifecycle ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
    app.state.arq = await create_pool(RedisSettings.from_dsn(REDIS_URL))
    from workers import init_db
    init_db()
    yield
    await app.state.redis.aclose()
    await app.state.arq.aclose()


app = FastAPI(title="DeployWatch API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting (simple in-memory per IP)
_rate_store: dict[str, list[float]] = {}

def check_rate_limit(ip: str, limit: int = 10, window: int = 60) -> bool:
    now = time.time()
    hits = [t for t in _rate_store.get(ip, []) if now - t < window]
    _rate_store[ip] = hits
    if len(hits) >= limit:
        return False
    _rate_store[ip].append(now)
    return True

Instrumentator().instrument(app).expose(app)


# ── Request / Response models ─────────────────────────────────────
class AnalyzeRequest(BaseModel):
    repo_url: str
    github_token: str | None = None


class LoadTestRequest(BaseModel):
    target_url: str
    concurrency: int = 10  # 10 | 50 | 100


# ── Endpoints ─────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = Path(__file__).parent / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    try:
        await app.state.redis.ping()
        return {"status": "ready"}
    except Exception:
        raise HTTPException(503, "Redis not reachable")


@app.post("/analyze")
async def analyze(req: AnalyzeRequest, request: Request):
    ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(ip):
        raise HTTPException(429, "Rate limit exceeded: max 10 requests/min")

    job = await app.state.arq.enqueue_job(
        "run_analysis",
        req.repo_url,
        req.github_token,
    )
    job_queue_depth.inc()
    return {"job_id": job.job_id}


@app.get("/status/{job_id}")
async def status(job_id: str):
    raw = await app.state.redis.get(f"job:{job_id}")
    if not raw:
        raise HTTPException(404, "Job not found")

    data = json.loads(raw)
    status_value = data.get("status")

    # Record terminal-job metrics only once so repeated polling stays safe.
    if status_value in {"done", "failed"} and not data.get("metrics_recorded"):
        job_queue_depth.dec()
        result = data.get("result", {})
        if status_value == "done" and result.get("pr_url"):
            pr_opened_total.inc()
        data["metrics_recorded"] = True
        await app.state.redis.set(f"job:{job_id}", json.dumps(data), ex=3600)

    return data


@app.post("/webhook/{repo_id}")
async def webhook(repo_id: str, request: Request):
    """GitHub push webhook — validates HMAC, enqueues re-scan."""
    body = await request.body()
    sig_header = request.headers.get("X-Hub-Signature-256", "")
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")

    if secret:
        expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig_header, expected):
            raise HTTPException(401, "Invalid webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")

    event = request.headers.get("X-GitHub-Event", "")
    if event != "push":
        return {"ignored": True, "event": event}

    repo_url = payload.get("repository", {}).get("clone_url", "")
    if not repo_url:
        raise HTTPException(400, "No repo URL in payload")

    job = await app.state.arq.enqueue_job("run_analysis", repo_url, None)
    job_queue_depth.inc()
    return {"queued": True, "job_id": job.job_id}


@app.get("/history/{owner}/{repo}")
async def history(owner: str, repo: str):
    """Return scan history for a repo."""
    repo_url_pattern = f"%github.com/{owner}/{repo}%"
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT score, grade, created_at FROM scans WHERE repo_url LIKE ? ORDER BY created_at DESC LIMIT 20",
        (repo_url_pattern,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/loadtest")
async def loadtest(req: LoadTestRequest, request: Request):
    """Fire concurrent requests and return latency percentiles."""
    import httpx
    import asyncio
    import statistics

    ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(ip, limit=2):
        raise HTTPException(429, "Load test rate limit: max 2/min")

    concurrency = min(req.concurrency, 100)
    latencies = []
    errors = 0

    async def fire(client: httpx.AsyncClient):
        nonlocal errors
        try:
            start = time.perf_counter()
            r = await client.get(req.target_url, timeout=10)
            latencies.append((time.perf_counter() - start) * 1000)
            if r.status_code >= 500:
                errors += 1
        except Exception:
            errors += 1

    async with httpx.AsyncClient() as client:
        await asyncio.gather(*[fire(client) for _ in range(concurrency)])

    if not latencies:
        return {"error": "All requests failed", "error_rate": 1.0}

    latencies.sort()
    n = len(latencies)

    def pct(p):
        return round(latencies[int(n * p / 100)], 2)

    return {
        "concurrency": concurrency,
        "total_requests": concurrency,
        "successful": n,
        "p50_ms": pct(50),
        "p95_ms": pct(95),
        "p99_ms": pct(99),
        "error_rate": round(errors / concurrency, 3),
    }
