from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path

from api.scanner import scan_repo
from api.scorer import score_repo
from api.fixer import generate_fixes
from api.pr_writer import open_pr

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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

    try:
        scan = scan_repo(req.repo_url)
    except ValueError as e:
        raise HTTPException(400, str(e))

    score = score_repo(scan)

    try:
        fixes = generate_fixes(scan, score)
    except Exception:
        fixes = []

    pr_url = None
    if fixes:
        try:
            pr_url = open_pr(req.repo_url, fixes, score)
        except Exception:
            pass

    score["fixes"] = fixes
    score["pr_url"] = pr_url
    return score
