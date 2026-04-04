import os
import json
import sqlite3
import httpx
from dotenv import load_dotenv
from arq.connections import RedisSettings

load_dotenv()

from scanner import scan_repo
from scorer import score_repo
from fixer import generate_fixes
from pr_writer import open_pr

DB_PATH = "deploywatch.db"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
SCORE_DROP_THRESHOLD = int(os.getenv("SCORE_DROP_THRESHOLD", "10"))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_url TEXT NOT NULL,
            score INTEGER NOT NULL,
            grade TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def get_previous_score(repo_url: str) -> int | None:
    conn = get_db()
    row = conn.execute(
        "SELECT score FROM scans WHERE repo_url = ? ORDER BY created_at DESC LIMIT 1",
        (repo_url,)
    ).fetchone()
    conn.close()
    return row["score"] if row else None


def save_scan(repo_url: str, result: dict):
    conn = get_db()
    conn.execute(
        "INSERT INTO scans (repo_url, score, grade, result_json) VALUES (?, ?, ?, ?)",
        (repo_url, result["score"], result["grade"], json.dumps(result))
    )
    conn.commit()
    conn.close()


async def fire_discord_alert(repo_url: str, old_score: int, new_score: int, issues: list[str]):
    if not DISCORD_WEBHOOK_URL:
        return

    drop = old_score - new_score
    issues_text = "\n".join(f"• {i}" for i in issues[:5])

    payload = {
        "embeds": [{
            "title": f"⚠️ DeployWatch Score Drop: {repo_url.split('/')[-1]}",
            "color": 0xFF4444,
            "fields": [
                {"name": "Repository", "value": repo_url, "inline": False},
                {"name": "Score", "value": f"{old_score} → {new_score} (−{drop} points)", "inline": True},
                {"name": "New grade", "value": "Critical Issues" if new_score < 50 else "Degraded", "inline": True},
                {"name": "Issues detected", "value": issues_text or "See dashboard for details", "inline": False},
            ],
            "footer": {"text": "DeployWatch — production readiness monitoring"}
        }]
    }

    async with httpx.AsyncClient() as client:
        try:
            await client.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        except Exception:
            pass  # Alert failure should never crash the job


async def run_analysis(ctx, repo_url: str, github_token: str | None = None):
    """
    Main ARQ background job. Runs the full pipeline:
    scan → score → fix → PR → alert check → save
    """
    redis = ctx["redis"]
    job_id = ctx["job_id"]

    async def set_status(status: str, result=None):
        data = {"status": status}
        if result is not None:
            data["result"] = result
        await redis.set(f"job:{job_id}", json.dumps(data), ex=3600)

    try:
        await set_status("cloning")
        scan_result = scan_repo(repo_url, github_token)

        await set_status("scoring")
        score_result = score_repo(scan_result)

        await set_status("fixing")
        fixes = generate_fixes(scan_result, score_result)

        await set_status("opening_pr")
        pr_url = None
        if fixes:
            try:
                token = github_token or os.getenv("GITHUB_TOKEN")
                if token:
                    pr_url = open_pr(repo_url, fixes, score_result, token)
            except Exception as e:
                score_result["pr_error"] = str(e)

        score_result["pr_url"] = pr_url
        score_result["fixes"] = fixes

        # Alert if score dropped significantly
        previous = get_previous_score(repo_url)
        if previous is not None and (previous - score_result["score"]) >= SCORE_DROP_THRESHOLD:
            await fire_discord_alert(repo_url, previous, score_result["score"], score_result["infra_gaps"])

        save_scan(repo_url, score_result)
        await set_status("done", score_result)

    except Exception as e:
        await set_status("failed", {"error": str(e)})
        raise


class WorkerSettings:
    functions = [run_analysis]
    redis_settings = RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://localhost:6379"))
    max_jobs = 10
    job_timeout = 300  # 5 minutes max per job
