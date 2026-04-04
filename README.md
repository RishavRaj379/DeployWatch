# DeployWatch

AI-powered production readiness agent. Paste a GitHub URL → get a score → Claude generates fixes → PR opened automatically.

## Setup (5 minutes)

### 1. Add your API keys
Open `api/config.py` and fill in:
```python
ANTHROPIC_API_KEY = "sk-ant-..."   # console.anthropic.com
GITHUB_TOKEN      = "ghp_..."      # github.com/settings/tokens (repo scope)
```

### 2. Run locally
```bash
pip install -r requirements.txt
uvicorn api.index:app --reload
# open http://localhost:8000
```

### 3. Deploy to Vercel
```bash
npm i -g vercel
vercel
```
Done. Vercel gives you a live URL.

## Stack
- FastAPI (Python)
- Claude API (fix generation)
- PyGithub (PR automation)
- GitPython (repo scanning)
- Vanilla JS frontend (no framework)
