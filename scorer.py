import re
from dataclasses import dataclass, field


@dataclass
class Cat:
    name: str
    score: int
    max_score: int
    issues: list[str] = field(default_factory=list)
    passed: list[str] = field(default_factory=list)


def _has(files, *patterns):
    for content in files.values():
        for p in patterns:
            if re.search(p, content, re.IGNORECASE):
                return True
    return False


def _file(files, *globs):
    for path in files:
        for g in globs:
            if g.lower() in path.lower():
                return True
    return False


def score_repo(scan: dict) -> dict:
    f = scan["files"]
    cats = []

    # 1. Health endpoints — 25pts
    c = Cat("Health Endpoints", 0, 25)
    if _has(f, r'/health', r'healthcheck'):
        c.score += 10; c.passed.append("/health endpoint found")
    else:
        c.issues.append("No /health endpoint")
    if _has(f, r'/ready', r'readiness'):
        c.score += 8; c.passed.append("Readiness probe found")
    else:
        c.issues.append("No readiness probe")
    if _has(f, r'/live', r'liveness', r'/ping'):
        c.score += 7; c.passed.append("Liveness probe found")
    else:
        c.issues.append("No liveness probe")
    cats.append(c)

    # 2. Observability — 20pts
    c = Cat("Observability", 0, 20)
    if _has(f, r'import logging', r'structlog', r'winston', r'pino'):
        c.score += 7; c.passed.append("Structured logging found")
    else:
        c.issues.append("No structured logging")
    if _has(f, r'prometheus', r'/metrics', r'datadog', r'opentelemetry'):
        c.score += 8; c.passed.append("Metrics instrumentation found")
    else:
        c.issues.append("No metrics (Prometheus / Datadog)")
    if _has(f, r'sentry', r'opentelemetry', r'jaeger'):
        c.score += 5; c.passed.append("Error tracking / tracing found")
    else:
        c.issues.append("No error tracking (Sentry etc.)")
    cats.append(c)

    # 3. Infra completeness — 20pts
    c = Cat("Infra Completeness", 0, 20)
    if _file(f, "dockerfile", "docker-compose"):
        c.score += 8; c.passed.append("Dockerfile found")
    else:
        c.issues.append("No Dockerfile")
    if _file(f, ".github/workflows", ".gitlab-ci", "jenkinsfile"):
        c.score += 7; c.passed.append("CI/CD pipeline found")
    else:
        c.issues.append("No CI/CD pipeline")
    if _file(f, ".tf", "terraform", "helm", "kubernetes"):
        c.score += 5; c.passed.append("IaC found")
    else:
        c.issues.append("No IaC (Terraform / Helm)")
    cats.append(c)

    # 4. Failure handling — 20pts
    c = Cat("Failure Handling", 0, 20)
    if _has(f, r'retry', r'backoff', r'tenacity'):
        c.score += 7; c.passed.append("Retry logic found")
    else:
        c.issues.append("No retry logic")
    if _has(f, r'timeout'):
        c.score += 7; c.passed.append("Timeouts configured")
    else:
        c.issues.append("No timeouts set")
    if _has(f, r'circuit.?break', r'pybreaker'):
        c.score += 6; c.passed.append("Circuit breaker found")
    else:
        c.issues.append("No circuit breaker")
    cats.append(c)

    # 5. Config safety — 10pts
    c = Cat("Config Safety", 0, 10)
    if _has(f, r'(password|secret|api_key)\s*=\s*["\'][^"\']{6,}["\']'):
        c.issues.append("Possible hardcoded secrets detected")
    else:
        c.score += 5; c.passed.append("No obvious hardcoded secrets")
    if _has(f, r'os\.environ', r'os\.getenv', r'process\.env', r'dotenv'):
        c.score += 5; c.passed.append("Env var usage found")
    else:
        c.issues.append("No env var usage detected")
    cats.append(c)

    # 6. Deployment readiness — 5pts
    c = Cat("Deployment Readiness", 0, 5)
    if _file(f, "readme"):
        c.score += 2; c.passed.append("README found")
    else:
        c.issues.append("No README")
    if _has(f, r'graceful', r'SIGTERM', r'shutdown'):
        c.score += 3; c.passed.append("Graceful shutdown found")
    else:
        c.issues.append("No graceful shutdown handling")
    cats.append(c)

    raw = sum(c.score for c in cats)
    capped = any(c.score == 0 for c in cats)
    final = min(raw, 60) if capped else raw

    grade = (
        "Production Ready" if final >= 90 else
        "Needs Attention" if final >= 70 else
        "Not Production Safe" if final >= 50 else
        "Critical Issues"
    )

    return {
        "repo_name": scan["repo_name"],
        "repo_url": scan["repo_url"],
        "score": final,
        "grade": grade,
        "capped": capped,
        "file_count": scan["file_count"],
        "categories": [
            {"name": c.name, "score": c.score, "max_score": c.max_score,
             "issues": c.issues, "passed": c.passed}
            for c in cats
        ],
        "infra_gaps": [i for c in cats for i in c.issues],
        "pr_url": None,
        "fixes": [],
    }
