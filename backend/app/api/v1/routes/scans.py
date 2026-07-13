import asyncio
from uuid import UUID

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.core.dependencies import DB, CurrentUser
from app.core.metrics import active_websocket_connections, scans_total
from app.models.scan import Finding, Scan, ScanStatus
from app.schemas.scan import ScanCreateRequest, ScanResponse, ScanSummaryResponse
from app.services.scan_service import hash_code, run_scan

router = APIRouter(prefix="/scans")
logger = structlog.get_logger()

# In-memory map of scan_id → asyncio.Queue for live WebSocket progress
_scan_queues: dict[str, asyncio.Queue] = {}


@router.post("", response_model=ScanResponse, status_code=201)
async def create_scan(
    body: ScanCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DB,
):
    if not body.code and not body.repo_url:
        raise HTTPException(status_code=400, detail="Provide either 'code' or 'repo_url'")

    code = body.code or ""
    scan = Scan(
        user_id=current_user.id,
        repo_url=body.repo_url,
        pr_number=body.pr_number,
        code_hash=hash_code(code),
        language=body.language or "unknown",
        status=ScanStatus.pending,
    )
    db.add(scan)
    await db.flush()
    await db.refresh(scan, attribute_names=["findings"])
    scan_id = scan.id

    # Create a queue now so the WebSocket can subscribe before bg task starts
    queue: asyncio.Queue = asyncio.Queue()
    _scan_queues[str(scan_id)] = queue

    # Background task uses its OWN session — not the request session
    background_tasks.add_task(_run_scan_with_own_session, scan_id, code, body.language, queue)
    scans_total.labels(status="pending").inc()
    return scan


async def _run_scan_with_own_session(
    scan_id: UUID,
    code: str,
    language: str | None,
    queue: asyncio.Queue,
) -> None:
    """Run scan in a fresh DB session independent of the HTTP request lifecycle."""
    async with AsyncSessionLocal() as db:
        try:
            await run_scan(db, scan_id, code, language, queue)
        except Exception as e:
            logger.error("background_scan_crashed", scan_id=str(scan_id), error=str(e))
        finally:
            # Remove queue once scan is done
            _scan_queues.pop(str(scan_id), None)


@router.get("", response_model=list[ScanSummaryResponse])
async def list_scans(current_user: CurrentUser, db: DB, skip: int = 0, limit: int = 20):
    result = await db.execute(
        select(Scan)
        .where(Scan.user_id == current_user.id)
        .order_by(Scan.created_at.desc())
        .offset(skip)
        .limit(min(limit, 100))
    )
    scans = result.scalars().all()

    # Attach finding counts efficiently
    output = []
    for scan in scans:
        findings_result = await db.execute(
            select(Finding).where(Finding.scan_id == scan.id)
        )
        findings = findings_result.scalars().all()
        summary = ScanSummaryResponse(
            id=scan.id,
            status=scan.status,
            language=scan.language,
            created_at=scan.created_at,
            completed_at=scan.completed_at,
            finding_count=len(findings),
            critical_count=sum(1 for f in findings if f.severity >= 9),
            high_count=sum(1 for f in findings if 7 <= f.severity < 9),
        )
        output.append(summary)
    return output


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Scan)
        .options(selectinload(Scan.findings))
        .where(Scan.id == scan_id, Scan.user_id == current_user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.delete("/{scan_id}", status_code=204)
async def delete_scan(scan_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id, Scan.user_id == current_user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    await db.delete(scan)


@router.websocket("/ws/{scan_id}")
async def scan_websocket(websocket: WebSocket, scan_id: UUID):
    await websocket.accept()
    active_websocket_connections.inc()
    sid = str(scan_id)

    try:
        # Check if scan already completed — stream from DB directly
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Scan).options(selectinload(Scan.findings)).where(Scan.id == scan_id)
            )
            scan = result.scalar_one_or_none()

        if not scan:
            await websocket.send_json({"event": "error", "message": "Scan not found"})
            return

        if scan.status == ScanStatus.done:
            for finding in sorted(scan.findings, key=lambda f: -f.severity):
                await websocket.send_json({
                    "event": "finding",
                    "finding": _finding_to_dict(finding),
                })
            await websocket.send_json({"event": "done", "progress_pct": 100})
            return

        if scan.status == ScanStatus.failed:
            await websocket.send_json({"event": "error", "message": scan.error_message or "Scan failed"})
            return

        # Scan is pending/running — subscribe to live queue
        queue = _scan_queues.get(sid)
        if queue is None:
            # Race: scan finished before WS connected — re-check DB
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Scan).options(selectinload(Scan.findings)).where(Scan.id == scan_id)
                )
                scan = result.scalar_one_or_none()
            if scan and scan.status == ScanStatus.done:
                for finding in sorted(scan.findings, key=lambda f: -f.severity):
                    await websocket.send_json({"event": "finding", "finding": _finding_to_dict(finding)})
                await websocket.send_json({"event": "done", "progress_pct": 100})
            else:
                await websocket.send_json({"event": "error", "message": "Scan queue not available"})
            return

        # Stream messages from queue until done
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=60.0)
                await websocket.send_json(msg)
                if msg.get("event") in ("done", "error"):
                    break
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"event": "ping"})
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info("websocket_disconnected", scan_id=sid)
    except Exception as e:
        logger.error("websocket_error", scan_id=sid, error=str(e))
    finally:
        active_websocket_connections.dec()


def _finding_to_dict(finding: Finding) -> dict:
    return {
        "id": str(finding.id),
        "title": finding.title,
        "owasp_category": finding.owasp_category,
        "severity": finding.severity,
        "severity_justification": finding.severity_justification,
        "description": finding.description,
        "vulnerable_code": finding.vulnerable_code,
        "fixed_code": finding.fixed_code,
        "fix_explanation": finding.fix_explanation,
        "diff_summary": finding.diff_summary,
        "line_start": finding.line_start,
        "line_end": finding.line_end,
        "function_name": finding.function_name,
    }
