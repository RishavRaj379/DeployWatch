import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path
import redis.asyncio as aioredis
from arq import create_pool
from arq.connections import RedisSettings

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")


class AnalyzeRequest(BaseModel):
    repo_url: str


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse((Path(__file__).parent.parent / "index.html").read_text())


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    if not req.repo_url.startswith("http"):
        raise HTTPException(400, "Invalid repo URL")
    pool = await create_pool(RedisSettings.from_dsn(REDIS_URL))
    job = await pool.enqueue_job("run_analysis", req.repo_url)
    await pool.aclose()
    return {"job_id": job.job_id}


@app.get("/api/status/{job_id}")
async def status(job_id: str):
    r = await aioredis.from_url(REDIS_URL)
    raw = await r.get(f"arq:result:{job_id}")
    await r.aclose()
    if raw is None:
        return {"status": "pending"}
    data = json.loads(raw)
    result = data.get("result", {})
    if isinstance(result, dict) and result.get("status") == "failed":
        return {"status": "failed", "error": result.get("error")}
    return {"status": "done", "result": result}
