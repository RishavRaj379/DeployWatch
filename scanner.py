import os
import shutil
import tempfile
from pathlib import Path
from git import Repo
from git.exc import GitCommandError
from api.config import GITHUB_TOKEN

MAX_FILE_SIZE = 50 * 1024
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next"}
SKIP_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2",
             ".ttf", ".eot", ".zip", ".tar", ".gz", ".bin", ".exe", ".lock", ".sum"}


def scan_repo(repo_url: str) -> dict:
    tmp_dir = tempfile.mkdtemp(prefix="dw_")

    url = repo_url
    if GITHUB_TOKEN and "github.com" in url:
        url = url.replace("https://", f"https://{GITHUB_TOKEN}@")

    try:
        Repo.clone_from(url, tmp_dir, depth=1)
    except GitCommandError as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise ValueError(f"Could not clone repo. Check the URL is correct and the repo is public. ({e})")

    files = {}
    root = Path(tmp_dir)

    try:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if set(path.relative_to(root).parts) & SKIP_DIRS:
                continue
            if path.suffix.lower() in SKIP_EXTS:
                continue
            if path.stat().st_size > MAX_FILE_SIZE:
                continue
            try:
                files[str(path.relative_to(root))] = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    repo_name = repo_url.rstrip("/").replace(".git", "").split("/")[-1]
    return {"repo_name": repo_name, "repo_url": repo_url, "files": files, "file_count": len(files)}
