from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.models.scan import ScanStatus


class ScanCreateRequest(BaseModel):
    code: Optional[str] = None
    repo_url: Optional[str] = None
    pr_number: Optional[int] = None
    language: Optional[str] = None

    @field_validator("code")
    @classmethod
    def code_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) == 0:
            raise ValueError("code cannot be empty")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "code": "def get_user(id):\n    query = f'SELECT * FROM users WHERE id={id}'\n    return db.execute(query)",
                "language": "python",
            }
        }
    }


class FindingResponse(BaseModel):
    id: UUID
    owasp_category: str
    title: str
    description: str
    severity: int
    severity_justification: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    vulnerable_code: str
    fixed_code: str
    fix_explanation: str
    diff_summary: str
    function_name: Optional[str] = None

    model_config = {"from_attributes": True}


class ScanResponse(BaseModel):
    id: UUID
    status: ScanStatus
    language: str
    repo_url: Optional[str] = None
    pr_number: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    findings: List[FindingResponse] = []
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class ScanSummaryResponse(BaseModel):
    id: UUID
    status: ScanStatus
    language: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    finding_count: int = 0
    critical_count: int = 0
    high_count: int = 0

    model_config = {"from_attributes": True}


class WsProgressMessage(BaseModel):
    event: str  # progress | finding | done | error | ping
    stage: Optional[str] = None
    finding: Optional[Any] = None   # dict at runtime, not FindingResponse (avoids UUID serialisation issues)
    message: Optional[str] = None
    progress_pct: Optional[int] = None
