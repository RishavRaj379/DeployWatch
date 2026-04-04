import json
import anthropic
from api.config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
MAX_CHARS = 80_000


def generate_fixes(scan: dict, score: dict) -> list[dict]:
    files = scan["files"]
    issues = score["infra_gaps"][:5]

    context = ""
    total = 0
    for path, content in files.items():
        chunk = f"\n--- {path} ---\n{content}\n"
        if total + len(chunk) > MAX_CHARS:
            break
        context += chunk
        total += len(chunk)

    issues_text = "\n".join(f"- {i}" for i in issues)

    prompt = f"""You are a senior SRE reviewing a GitHub repo for production readiness.

Repo: {scan['repo_name']}
Score: {score['score']}/100 ({score['grade']})

Top issues:
{issues_text}

Files:
{context}

Generate fixes for the top 3 issues. Reply ONLY with a JSON array, no markdown:

[
  {{
    "file": "path/to/file",
    "explanation": "one sentence what this fixes",
    "old_content": "current file content or empty string if new file",
    "new_content": "full new file content with fix applied"
  }}
]"""

    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        fixes = json.loads(raw)
    except Exception:
        return []

    return [f for f in fixes if all(k in f for k in ("file", "explanation", "old_content", "new_content"))]
