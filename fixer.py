import os
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MAX_CONTEXT_CHARS = 80_000  # Stay within token limits


def _build_file_context(files: dict) -> str:
    """Build a trimmed string of file contents for the prompt."""
    lines = []
    total = 0
    for path, content in files.items():
        chunk = f"\n--- {path} ---\n{content}\n"
        if total + len(chunk) > MAX_CONTEXT_CHARS:
            break
        lines.append(chunk)
        total += len(chunk)
    return "".join(lines)


def generate_fixes(scan_result: dict, score_result: dict) -> list[dict]:
    """
    Send repo context + issues to Claude and get back specific file fixes.
    Returns list of {file, old_content, new_content, explanation}.
    """
    files = scan_result["files"]
    issues = score_result["infra_gaps"][:5]  # Top 5 issues
    file_context = _build_file_context(files)

    issues_text = "\n".join(f"- {i}" for i in issues)

    prompt = f"""You are a senior SRE reviewing a GitHub repository for production readiness.

Repository: {scan_result['repo_name']}
Current score: {score_result['score']}/100 ({score_result['grade']})

Top issues found:
{issues_text}

Here are the repository files:
{file_context}

Your task: Generate specific fixes for the top 3 most critical issues above.
For each fix, respond with a JSON array (and nothing else) in this exact format:

[
  {{
    "file": "path/to/file.py",
    "explanation": "One sentence: what this fixes and why it matters",
    "old_content": "the exact current content of the file (or empty string if new file)",
    "new_content": "the full new content of the file with the fix applied"
  }}
]

Rules:
- Only fix files that actually exist in the repo, OR create new files if essential (like Dockerfile, health endpoint)
- Make real, working code changes — not placeholders
- Keep fixes minimal and targeted — don't rewrite entire files
- If you must create a new file, set old_content to empty string
- Respond with ONLY the JSON array, no markdown, no explanation outside the array
"""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    import json
    try:
        fixes = json.loads(raw)
    except json.JSONDecodeError:
        # Best-effort: return empty if Claude's response isn't parseable
        return []

    # Validate structure
    valid = []
    for fix in fixes:
        if isinstance(fix, dict) and all(k in fix for k in ("file", "explanation", "old_content", "new_content")):
            valid.append(fix)

    return valid
