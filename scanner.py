import os
import shutil
import tempfile
from pathlib import Path
from git import Repo
from git.exc import GitCommandError

MAX_FILE_SIZE = 50 * 1024  # 50KB
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next"}
SKIP_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot",
             ".zip", ".tar", ".gz", ".bin", ".exe", ".lock", ".sum"}


def clone_repo(repo_url: str, github_token: str | None = None) -> tuple[str, str]:
    """Clone a repo to a temp dir. Returns (tmp_dir, repo_name)."""
    tmp_dir = tempfile.mkdtemp(prefix="deploywatch_")

    # Inject token for private repos
    if github_token and "github.com" in repo_url:
        repo_url = repo_url.replace("https://", f"https://{github_token}@")

    try:
        Repo.clone_from(repo_url, tmp_dir, depth=1)
    except GitCommandError as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        if "Authentication failed" in str(e) or "not found" in str(e).lower():
            raise ValueError("Repo not found or authentication failed. For private repos, provide a GitHub token.")
        raise ValueError(f"Failed to clone repo: {e}")

    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    return tmp_dir, repo_name


def scan_repo(repo_url: str, github_token: str | None = None) -> dict:
    """
    Clone the repo and return a dict of {filepath: content}.
    Only includes text files under 50KB. Cleans up after itself.
    """
    tmp_dir, repo_name = clone_repo(repo_url, github_token)

    files = {}
    root = Path(tmp_dir)

    try:
        for path in root.rglob("*"):
            if not path.is_file():
                continue

            # Skip unwanted dirs
            parts = set(path.relative_to(root).parts)
            if parts & SKIP_DIRS:
                continue

            # Skip unwanted extensions
            if path.suffix.lower() in SKIP_EXTS:
                continue

            # Skip large files
            if path.stat().st_size > MAX_FILE_SIZE:
                continue

            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(path.relative_to(root))
                files[rel_path] = content
            except Exception:
                continue
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return {
        "repo_name": repo_name,
        "repo_url": repo_url,
        "files": files,
        "file_count": len(files),
    }
