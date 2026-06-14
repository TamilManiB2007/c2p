from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict
from app.models.compliance import ComplianceStatus


class ComplianceRunRequest(BaseModel):
    """Request schema for running a compliance check."""
    contract_id: int
    invoice_id: int


class ComplianceCheckResponse(BaseModel):
    """Response schema containing the compliance check details."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_id: int
    invoice_id: int
    check_type: str
    status: ComplianceStatus
    details: dict
    created_at: datetime


class ComplianceListResponse(BaseModel):
    """Paginated list of compliance checks."""
    checks: List[ComplianceCheckResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
