import re
from dataclasses import dataclass, field


@dataclass
class CategoryResult:
    name: str
    score: int
    max_score: int
    issues: list[str] = field(default_factory=list)
    passed: list[str] = field(default_factory=list)


def _has_pattern(files: dict, *patterns: str) -> bool:
    """Check if any file content matches any of the given regex patterns."""
    for content in files.values():
        for p in patterns:
            if re.search(p, content, re.IGNORECASE):
                return True
    return False


def _file_exists(files: dict, *globs: str) -> bool:
    """Check if any file path matches any of the given substrings."""
    for path in files:
        for g in globs:
            if g.lower() in path.lower():
                return True
    return False


def score_health_endpoints(files: dict) -> CategoryResult:
    """25 pts — health/readiness/liveness endpoints."""
    result = CategoryResult("Health Endpoints", 0, 25)

    if _has_pattern(files, r'/health', r'healthcheck', r'health_check'):
        result.score += 10
        result.passed.append("/health endpoint found")
    else:
        result.issues.append("No /health endpoint — required for load balancers and orchestrators")

    if _has_pattern(files, r'/ready', r'readiness', r'readyz'):
        result.score += 8
        result.passed.append("/ready or readiness endpoint found")
    else:
        result.issues.append("No readiness probe — Kubernetes won't know when app is ready")

    if _has_pattern(files, r'/live', r'liveness', r'livez', r'/ping'):
        result.score += 7
        result.passed.append("/live or /ping endpoint found")
    else:
        result.issues.append("No liveness probe — orchestrators can't detect hung processes")

    return result


def score_observability(files: dict) -> CategoryResult:
    """20 pts — logging, metrics, tracing."""
    result = CategoryResult("Observability", 0, 20)

    if _has_pattern(files, r'import logging', r'from logging', r'logger\s*=', r'winston', r'pino', r'structlog'):
        result.score += 7
        result.passed.append("Structured logging detected")
    else:
        result.issues.append("No structured logging — use logging/structlog/winston for parseable logs")

    if _has_pattern(files, r'prometheus', r'/metrics', r'statsd', r'datadog', r'opentelemetry'):
        result.score += 8
        result.passed.append("Metrics instrumentation found")
    else:
        result.issues.append("No metrics — add Prometheus or similar for observability")

    if _has_pattern(files, r'trace', r'opentelemetry', r'jaeger', r'zipkin', r'sentry'):
        result.score += 5
        result.passed.append("Tracing / error tracking found")
    else:
        result.issues.append("No distributed tracing or error tracking (Sentry, OpenTelemetry)")

    return result


def score_infra_completeness(files: dict) -> CategoryResult:
    """20 pts — Docker, CI/CD, IaC."""
    result = CategoryResult("Infra Completeness", 0, 20)

    if _file_exists(files, "dockerfile", "docker-compose"):
        result.score += 8
        result.passed.append("Dockerfile or docker-compose found")
    else:
        result.issues.append("No Dockerfile — app cannot be containerised consistently")

    if _file_exists(files, ".github/workflows", ".gitlab-ci", "jenkinsfile", "circleci", ".travis"):
        result.score += 7
        result.passed.append("CI/CD pipeline config found")
    else:
        result.issues.append("No CI/CD pipeline — add GitHub Actions or equivalent")

    if _file_exists(files, ".tf", "terraform", "pulumi", "cdk", "helm", "k8s", "kubernetes"):
        result.score += 5
        result.passed.append("IaC / Kubernetes manifests found")
    else:
        result.issues.append("No IaC found (Terraform, Helm, CDK) — infra should be code")

    return result


def score_failure_handling(files: dict) -> CategoryResult:
    """20 pts — retries, timeouts, circuit breakers, error handling."""
    result = CategoryResult("Failure Handling", 0, 20)

    if _has_pattern(files, r'retry', r'backoff', r'tenacity', r'retrying'):
        result.score += 7
        result.passed.append("Retry logic found")
    else:
        result.issues.append("No retry logic — transient failures will cause hard errors")

    if _has_pattern(files, r'timeout', r'connect_timeout', r'read_timeout', r'socket\.settimeout'):
        result.score += 7
        result.passed.append("Timeouts configured")
    else:
        result.issues.append("No timeouts set — network calls can hang indefinitely")

    if _has_pattern(files, r'circuit.?break', r'hystrix', r'resilience4j', r'pybreaker'):
        result.score += 6
        result.passed.append("Circuit breaker pattern found")
    else:
        result.issues.append("No circuit breaker — cascading failures are possible")

    return result


def score_config_safety(files: dict) -> CategoryResult:
    """10 pts — no hardcoded secrets, uses env vars."""
    result = CategoryResult("Config Safety", 0, 10)

    secret_pattern = r'(password|secret|api_key|apikey|token)\s*=\s*["\'][^"\']{6,}["\']'
    if _has_pattern(files, secret_pattern):
        result.issues.append("Possible hardcoded secrets detected — use environment variables")
    else:
        result.score += 5
        result.passed.append("No obvious hardcoded secrets")

    if _has_pattern(files, r'os\.environ', r'os\.getenv', r'process\.env', r'dotenv', r'from_env'):
        result.score += 5
        result.passed.append("Environment variable usage found")
    else:
        result.issues.append("No env var usage detected — config should come from the environment")

    return result


def score_deployment_readiness(files: dict) -> CategoryResult:
    """5 pts — README, graceful shutdown."""
    result = CategoryResult("Deployment Readiness", 0, 5)

    if _file_exists(files, "readme"):
        result.score += 2
        result.passed.append("README found")
    else:
        result.issues.append("No README — document how to run and deploy this service")

    if _has_pattern(files, r'graceful', r'SIGTERM', r'shutdown', r'on_shutdown', r'lifespan'):
        result.score += 3
        result.passed.append("Graceful shutdown handling found")
    else:
        result.issues.append("No graceful shutdown — in-flight requests may be dropped on deploy")

    return result


def compute_grade(score: int) -> str:
    if score >= 90:
        return "Production Ready"
    elif score >= 70:
        return "Needs Attention"
    elif score >= 50:
        return "Not Production Safe"
    else:
        return "Critical Issues"


def score_repo(scan_result: dict) -> dict:
    """Run all scoring categories and return the full report dict."""
    files = scan_result["files"]

    categories = [
        score_health_endpoints(files),
        score_observability(files),
        score_infra_completeness(files),
        score_failure_handling(files),
        score_config_safety(files),
        score_deployment_readiness(files),
    ]

    raw_score = sum(c.score for c in categories)
    max_score = sum(c.max_score for c in categories)

    # Critical failure cap: if any category scores 0, cap total at 60
    has_critical_failure = any(c.score == 0 for c in categories)
    final_score = min(raw_score, 60) if has_critical_failure else raw_score

    all_issues = [issue for c in categories for issue in c.issues]

    return {
        "repo_name": scan_result["repo_name"],
        "repo_url": scan_result["repo_url"],
        "score": final_score,
        "max_score": max_score,
        "grade": compute_grade(final_score),
        "capped": has_critical_failure,
        "categories": [
            {
                "name": c.name,
                "score": c.score,
                "max_score": c.max_score,
                "issues": c.issues,
                "passed": c.passed,
            }
            for c in categories
        ],
        "infra_gaps": all_issues,
        "file_count": scan_result["file_count"],
        "pr_url": None,
        "load_results": None,
    }
