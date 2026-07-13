import time

import httpx
import structlog
from jose import jwt as jose_jwt

from app.core.config import settings

logger = structlog.get_logger()

GITHUB_API = "https://api.github.com"


def _make_jwt() -> str:
    """Create a GitHub App JWT valid for 10 minutes, signed with RS256."""
    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 600, "iss": settings.GITHUB_APP_ID}
    private_key = settings.GITHUB_PRIVATE_KEY.replace("\\n", "\n")
    return jose_jwt.encode(payload, private_key, algorithm="RS256")


async def get_installation_token(installation_id: int) -> str:
    app_jwt = _make_jwt()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GITHUB_API}/app/installations/{installation_id}/access_tokens",
            headers={"Authorization": f"Bearer {app_jwt}", "Accept": "application/vnd.github+json"},
        )
        resp.raise_for_status()
        return resp.json()["token"]


async def get_pr_diff(repo: str, pr_number: int, token: str) -> list[dict]:
    """Return list of {filename, patch, line_count} for a PR."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}/files", headers=headers)
        resp.raise_for_status()
        files = resp.json()
        return [
            {
                "filename": f["filename"],
                "patch": f.get("patch", ""),
                "additions": f.get("additions", 0),
                "raw_url": f.get("raw_url", ""),
            }
            for f in files
            if f.get("patch")
        ]


async def get_file_content(repo: str, path: str, ref: str, token: str) -> str:
    import base64
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GITHUB_API}/repos/{repo}/contents/{path}?ref={ref}", headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return base64.b64decode(data["content"]).decode("utf-8")


async def post_pr_review(
    repo: str, pr_number: int, token: str, findings: list[dict], scan_id: str
) -> None:
    """Post a PR review with inline suggestions for each finding."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Summary comment body
    rows = "\n".join(
        f"| {f['owasp_category']} | {f['title']} | {'🔴' if f['severity'] >= 9 else '🟠' if f['severity'] >= 7 else '🟡' if f['severity'] >= 4 else '🟢'} {f['severity']}/10 |"
        for f in sorted(findings, key=lambda x: -x["severity"])
    )
    body = (
        f"## 🔒 AI Code Security Scanner — Scan `{scan_id[:8]}`\n\n"
        f"Found **{len(findings)}** vulnerabilities.\n\n"
        f"| OWASP Category | Title | Severity |\n|---|---|---|\n{rows}\n\n"
        f"*Powered by AI Code Security Scanner. Accept suggestions inline to apply fixes.*"
    )

    # Build inline comments
    comments = []
    for f in findings:
        if f.get("line_start") and f.get("filename"):
            suggestion = f"\n```suggestion\n{f['fixed_code']}\n```"
            comment_body = (
                f"### ⚠️ {f['title']}\n"
                f"**{f['owasp_category']}** — Severity {f['severity']}/10\n\n"
                f"{f['description']}\n\n"
                f"**Fix:** {f['fix_explanation']}\n"
                f"{suggestion}"
            )
            comments.append({
                "path": f["filename"],
                "line": f["line_start"],
                "side": "RIGHT",
                "body": comment_body,
            })

    payload = {"body": body, "event": "COMMENT", "comments": comments}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}/reviews",
            headers=headers,
            json=payload,
        )
        if resp.status_code not in (200, 201):
            logger.error("pr_review_post_failed", status=resp.status_code, body=resp.text)
        else:
            logger.info("pr_review_posted", repo=repo, pr=pr_number)
