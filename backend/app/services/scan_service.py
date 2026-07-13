import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.metrics import (
    groq_api_calls_total,
    scan_cache_hits_total,
    scan_duration_seconds,
    scan_findings_total,
    scans_total,
)
from app.core.redis import get_redis
from app.models.scan import Finding, Scan, ScanStatus
from app.schemas.scan import WsProgressMessage
from app.services.scanner.ai_client import classify_owasp, generate_fix, score_severity
from app.services.scanner.chunker import chunk_code
from app.services.scanner.language_detector import detect_language

logger = structlog.get_logger()

PROMPT_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "disregard your instructions",
    "you are now",
    "new persona",
    "jailbreak",
    "forget everything",
    "act as if",
]

_SEVERITY_BAND = {
    range(9, 11): "critical",
    range(7, 9): "high",
    range(4, 7): "medium",
    range(1, 4): "low",
}


def _severity_band(s: int) -> str:
    for r, label in _SEVERITY_BAND.items():
        if s in r:
            return label
    return "low"


def _validate_input(code: str) -> None:
    """Raise ValueError for oversized, malformed, or injected input."""
    size_kb = len(code.encode()) / 1024
    if size_kb > settings.MAX_CODE_SIZE_KB:
        raise ValueError(f"Code exceeds {settings.MAX_CODE_SIZE_KB}KB limit ({size_kb:.1f}KB)")
    if len(code.splitlines()) > settings.MAX_CODE_LINES:
        raise ValueError(f"Code exceeds {settings.MAX_CODE_LINES} line limit")
    if "\x00" in code:
        raise ValueError("Code contains null bytes")
    code_lower = code.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern in code_lower:
            raise ValueError("Potential prompt injection detected in input")


async def run_scan(
    db: AsyncSession,
    scan_id: UUID,
    code: str,
    language: Optional[str] = None,
    progress_queue: Optional[asyncio.Queue] = None,
) -> None:
    """Full pipeline: validate → chunk → classify → score → fix → persist."""
    t_start = time.perf_counter()
    redis = await get_redis()

    scan = await db.get(Scan, scan_id)
    if not scan:
        logger.error("scan_not_found", scan_id=str(scan_id))
        return

    async def _emit(msg: WsProgressMessage) -> None:
        if progress_queue:
            # Put to all subscribers (broadcast by copying queue ref)
            await progress_queue.put(msg.model_dump(mode="json"))

    try:
        _validate_input(code)
        lang = detect_language(code, language)
        scan.language = lang
        scan.status = ScanStatus.running
        await db.commit()

        # ── Cache check ───────────────────────────────────────
        cache_key = f"scan:result:{scan.code_hash}"
        cached_raw = await redis.get(cache_key)
        if cached_raw:
            logger.info("scan_cache_hit", scan_id=str(scan_id))
            scan_cache_hits_total.inc()
            cached_findings: list[dict] = json.loads(cached_raw)
            for f_data in cached_findings:
                db.add(Finding(scan_id=scan_id, **f_data))
            scan.status = ScanStatus.done
            scan.completed_at = datetime.now(timezone.utc)
            await db.commit()
            scans_total.labels(status="done").inc()
            await _emit(WsProgressMessage(event="done", progress_pct=100))
            return

        # ── Chunk ─────────────────────────────────────────────
        await _emit(WsProgressMessage(event="progress", stage="Chunking code", progress_pct=5))
        chunks = chunk_code(code, lang)
        total_chunks = max(len(chunks), 1)
        logger.info("scan_started", scan_id=str(scan_id), chunks=total_chunks, language=lang)

        all_findings_data: list[dict] = []

        for idx, chunk in enumerate(chunks):
            pct = 10 + int((idx / total_chunks) * 80)
            await _emit(WsProgressMessage(
                event="progress",
                stage=f"Classifying {chunk.function_name}",
                progress_pct=pct,
            ))

            # Classify
            groq_api_calls_total.labels(stage="classify").inc()
            raw_findings = await classify_owasp(chunk.code, chunk.language, chunk.function_name)

            if not raw_findings:
                continue

            await _emit(WsProgressMessage(
                event="progress",
                stage=f"Scoring & fixing {len(raw_findings)} finding(s) in {chunk.function_name}",
                progress_pct=pct + 2,
            ))

            # Score + fix all findings in this chunk concurrently
            tasks = [
                _process_finding(f, chunk.language, chunk.line_start)
                for f in raw_findings
            ]
            gathered: list[dict | BaseException] = await asyncio.gather(*tasks, return_exceptions=True)

            for item in gathered:
                if isinstance(item, BaseException):
                    logger.warning("finding_process_error", error=str(item))
                    continue

                result: dict = item
                finding = Finding(scan_id=scan_id, **result)
                db.add(finding)
                await db.flush()  # get finding.id populated
                all_findings_data.append(result)

                # Emit finding to WebSocket subscribers
                scan_findings_total.labels(severity_band=_severity_band(result["severity"])).inc()
                await _emit(WsProgressMessage(
                    event="finding",
                    finding={**result, "id": str(finding.id)},
                ))

        await db.commit()

        # ── Cache for dedup ───────────────────────────────────
        try:
            await redis.set(cache_key, json.dumps(all_findings_data), ex=settings.SCAN_CACHE_TTL_SECONDS)
        except Exception as cache_err:
            logger.warning("cache_set_failed", error=str(cache_err))

        scan.status = ScanStatus.done
        scan.completed_at = datetime.now(timezone.utc)
        await db.commit()

        duration = time.perf_counter() - t_start
        scan_duration_seconds.observe(duration)
        scans_total.labels(status="done").inc()

        await _emit(WsProgressMessage(event="done", progress_pct=100))
        logger.info(
            "scan_complete",
            scan_id=str(scan_id),
            findings=len(all_findings_data),
            duration_s=round(duration, 2),
            language=lang,
        )

    except Exception as e:
        logger.error("scan_failed", scan_id=str(scan_id), error=str(e), exc_info=True)
        try:
            scan.status = ScanStatus.failed
            scan.error_message = str(e)[:1000]
            await db.commit()
        except Exception:
            pass
        scans_total.labels(status="failed").inc()
        await _emit(WsProgressMessage(event="error", message=str(e)))


async def _process_finding(raw: dict, language: str, line_offset: int) -> dict:
    """Score and fix a single raw finding. Returns a dict ready for the Finding model."""
    owasp = str(raw.get("owasp_category", "Unknown"))
    title = str(raw.get("title", "Vulnerability"))
    description = str(raw.get("description", ""))
    vuln_code = str(raw.get("vulnerable_code", ""))
    line_start = raw.get("line_start") or line_offset
    line_end = raw.get("line_end") or line_start

    groq_api_calls_total.labels(stage="score").inc()
    groq_api_calls_total.labels(stage="fix").inc()

    (severity, justification), (fixed_code, explanation, diff_summary) = await asyncio.gather(
        score_severity(owasp, title, description, vuln_code, language),
        generate_fix(owasp, title, description, vuln_code, language),
    )

    return {
        "owasp_category": owasp,
        "title": title,
        "description": description,
        "severity": severity,
        "severity_justification": justification,
        "line_start": line_start,
        "line_end": line_end,
        "vulnerable_code": vuln_code,
        "fixed_code": fixed_code,
        "fix_explanation": explanation,
        "diff_summary": diff_summary,
        "function_name": raw.get("function_name"),
    }


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()
