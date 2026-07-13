import hashlib
import hmac
import json
import uuid

import structlog
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.scan import Scan, ScanStatus
from app.models.user import User, UserRole

router = APIRouter(prefix="/github")
logger = structlog.get_logger()

# Deterministic system user ID used for scans triggered by GitHub webhooks
# (not user-initiated). Created lazily on first webhook if it doesn't exist.
SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SYSTEM_USER_EMAIL = "github-bot@system.internal"


def _verify_signature(body: bytes, signature: str) -> bool:
    if not settings.GITHUB_WEBHOOK_SECRET:
        logger.error("webhook_secret_not_configured")
        return False
    expected = "sha256=" + hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _ensure_system_user(db) -> uuid.UUID:
    """Get or create the system user that owns webhook-triggered scans."""
    existing = await db.get(User, SYSTEM_USER_ID)
    if existing:
        return existing.id

    result = await db.execute(select(User).where(User.email == SYSTEM_USER_EMAIL))
    found = result.scalar_one_or_none()
    if found:
        return found.id

    # Random unusable password hash — this account can never log in via the API
    system_user = User(
        id=SYSTEM_USER_ID,
        email=SYSTEM_USER_EMAIL,
        hashed_password="!disabled!",
        role=UserRole.admin,
    )
    db.add(system_user)
    await db.flush()
    return system_user.id


@router.post("/webhook")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(...),
    x_hub_signature_256: str = Header(...),
):
    body = await request.body()

    if not _verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    action = payload.get("action")

    if x_github_event == "pull_request" and action in ("opened", "synchronize", "reopened"):
        try:
            repo = payload["repository"]["full_name"]
            pr_number = payload["pull_request"]["number"]
            installation_id = payload["installation"]["id"]
        except KeyError as e:
            raise HTTPException(status_code=400, detail=f"Missing required field: {e}")

        background_tasks.add_task(_handle_pr, repo, pr_number, installation_id)

    return {"status": "accepted"}


async def _handle_pr(repo: str, pr_number: int, installation_id: int) -> None:
    """Fetch PR diff, run scan, post results as a PR review with inline fix suggestions."""
    try:
        from app.services.github.github_client import get_installation_token, get_pr_diff, post_pr_review
        from app.services.scan_service import hash_code, run_scan

        token = await get_installation_token(installation_id)
        files = await get_pr_diff(repo, pr_number, token)

        if not files:
            logger.info("pr_no_changed_files", repo=repo, pr=pr_number)
            return

        # Scan each changed file separately so we can map findings back to filenames
        async with AsyncSessionLocal() as db:
            system_user_id = await _ensure_system_user(db)
            await db.commit()

            all_findings_with_file: list[dict] = []

            for f in files:
                code = f.get("patch", "")
                if not code.strip():
                    continue

                scan = Scan(
                    user_id=system_user_id,
                    repo_url=f"https://github.com/{repo}",
                    pr_number=pr_number,
                    code_hash=hash_code(f"{repo}:{pr_number}:{f['filename']}:{code}"),
                    language="unknown",
                    status=ScanStatus.pending,
                )
                db.add(scan)
                await db.flush()
                scan_id = scan.id

                await run_scan(db, scan_id, code)

                result = await db.execute(
                    select(Scan).options(selectinload(Scan.findings)).where(Scan.id == scan_id)
                )
                completed = result.scalar_one()

                for finding in completed.findings:
                    all_findings_with_file.append({
                        "owasp_category": finding.owasp_category,
                        "title": finding.title,
                        "description": finding.description,
                        "severity": finding.severity,
                        "fix_explanation": finding.fix_explanation,
                        "fixed_code": finding.fixed_code,
                        "line_start": finding.line_start,
                        "filename": f["filename"],
                    })

            if all_findings_with_file:
                await post_pr_review(
                    repo, pr_number, token, all_findings_with_file,
                    scan_id=f"{repo}-pr{pr_number}",
                )
                logger.info(
                    "pr_review_complete", repo=repo, pr=pr_number,
                    findings=len(all_findings_with_file),
                )
            else:
                logger.info("pr_no_findings", repo=repo, pr=pr_number)

    except Exception as e:
        logger.error("pr_handler_failed", repo=repo, pr=pr_number, error=str(e), exc_info=True)
