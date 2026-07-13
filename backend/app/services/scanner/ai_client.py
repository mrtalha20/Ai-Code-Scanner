import json
from typing import Any

import structlog
from groq import APITimeoutError, AsyncGroq, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.services.scanner.prompts import (
    FIX_GENERATOR_SYSTEM,
    FIX_GENERATOR_USER,
    OWASP_CLASSIFIER_SYSTEM,
    OWASP_CLASSIFIER_USER,
    SEVERITY_SCORER_SYSTEM,
    SEVERITY_SCORER_USER,
)

logger = structlog.get_logger()

# Groq's SDK is OpenAI-compatible — same interface, just different client + base URL
client = AsyncGroq(api_key=settings.GROQ_API_KEY)


def _parse_json(text: str) -> Any:
    """Strip markdown fences and parse JSON safely."""
    text = text.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:])
        text = text.rstrip("`").strip()
    return json.loads(text)


@retry(
    retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
)
async def _call_groq(system: str, user: str) -> str:
    """Call Groq API. Groq enforces JSON mode via response_format when supported."""
    response = await client.chat.completions.create(
        model=settings.GROQ_MODEL,
        max_tokens=settings.GROQ_MAX_TOKENS,
        temperature=0.1,
        # Groq supports response_format for JSON mode on most models
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content or ""


async def classify_owasp(code: str, language: str, function_name: str) -> list[dict]:
    """Return list of raw finding dicts from Groq."""
    user_prompt = OWASP_CLASSIFIER_USER.format(
        language=language,
        function_name=function_name,
        code=code,
    )
    try:
        raw = await _call_groq(OWASP_CLASSIFIER_SYSTEM, user_prompt)
        result = _parse_json(raw)
        # Groq JSON mode may wrap the array in a key — unwrap if needed
        if isinstance(result, dict):
            for key in ("findings", "vulnerabilities", "results", "items"):
                if isinstance(result.get(key), list):
                    result = result[key]
                    break
            else:
                result = []
        return result if isinstance(result, list) else []
    except Exception as e:
        logger.error("owasp_classify_failed", error=str(e), function=function_name)
        return []


async def score_severity(
    owasp_category: str, title: str, description: str, vulnerable_code: str, language: str
) -> tuple[int, str]:
    """Return (severity 1-10, justification)."""
    user_prompt = SEVERITY_SCORER_USER.format(
        language=language,
        owasp_category=owasp_category,
        title=title,
        description=description,
        vulnerable_code=vulnerable_code,
    )
    try:
        raw = await _call_groq(SEVERITY_SCORER_SYSTEM, user_prompt)
        data = _parse_json(raw)
        severity = max(1, min(10, int(data.get("severity", 5))))
        justification = str(data.get("justification", ""))
        return severity, justification
    except Exception as e:
        logger.error("severity_score_failed", error=str(e))
        return 5, "Scoring unavailable"


async def generate_fix(
    owasp_category: str, title: str, description: str, vulnerable_code: str, language: str
) -> tuple[str, str, str]:
    """Return (fixed_code, explanation, diff_summary)."""
    user_prompt = FIX_GENERATOR_USER.format(
        language=language,
        owasp_category=owasp_category,
        title=title,
        description=description,
        vulnerable_code=vulnerable_code,
    )
    try:
        raw = await _call_groq(FIX_GENERATOR_SYSTEM, user_prompt)
        data = _parse_json(raw)
        return (
            str(data.get("fixed_code", vulnerable_code)),
            str(data.get("explanation", "")),
            str(data.get("diff_summary", "")),
        )
    except Exception as e:
        logger.error("fix_generate_failed", error=str(e))
        return vulnerable_code, "Fix generation failed", ""
