"""
Compliance API Router — Phase 4: Compliance Foundation

Endpoints:
  POST   /compliance/run             — Run compliance check
  GET    /compliance/checks/{id}     — Get compliance results
  GET    /compliance/violations      — List violations (failed checks)
  GET    /compliance/violations/{id} — Get violation details (must be a failed check)

All endpoints require a valid JWT bearer token.
"""
from typing import List, Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.compliance import ComplianceStatus
from app.schemas.compliance import (
    ComplianceRunRequest,
    ComplianceCheckResponse,
    ComplianceListResponse,
)
from app.services.compliance_service import ComplianceService

router = APIRouter(prefix="/compliance", tags=["Compliance"])


# ---------------------------------------------------------------------------
# POST /compliance/run
# ---------------------------------------------------------------------------
@router.post(
    "/run",
    response_model=ComplianceCheckResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run compliance check",
    description="Evaluate deterministic compliance rules for a contract-invoice pair.",
)
async def run_compliance_check(
    request: ComplianceRunRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    compliance_service = ComplianceService(db)
    check = await compliance_service.run_check(request.contract_id, request.invoice_id)
    return check


# ---------------------------------------------------------------------------
# GET /compliance/checks/{check_id}
# ---------------------------------------------------------------------------
@router.get(
    "/checks/{check_id}",
    response_model=ComplianceCheckResponse,
    summary="Get compliance results",
    description="Retrieve the details and rule verification status of a compliance check.",
)
async def get_compliance_results(
    check_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    compliance_service = ComplianceService(db)
    check = await compliance_service.get_check_by_id(check_id)
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance check with id={check_id} not found",
        )
    return check


# ---------------------------------------------------------------------------
# GET /compliance/violations
# ---------------------------------------------------------------------------
@router.get(
    "/violations",
    response_model=List[ComplianceCheckResponse],
    summary="List violations",
    description="Retrieve a paginated list of failed compliance checks.",
)
async def list_violations(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    compliance_service = ComplianceService(db)
    violations, _ = await compliance_service.get_violations(page=page, page_size=page_size)
    return violations


# ---------------------------------------------------------------------------
# GET /compliance/violations/{check_id}
# ---------------------------------------------------------------------------
@router.get(
    "/violations/{check_id}",
    response_model=ComplianceCheckResponse,
    summary="Get violation details",
    description="Retrieve details of a failed compliance check. Returns 404 if the check is not a violation.",
)
async def get_violation_details(
    check_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    compliance_service = ComplianceService(db)
    check = await compliance_service.get_check_by_id(check_id)
    if not check or check.status != ComplianceStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Violation with check_id={check_id} not found",
        )
    return check


# ---------------------------------------------------------------------------
# GET /compliance/checks
# ---------------------------------------------------------------------------
@router.get(
    "/checks",
    response_model=ComplianceListResponse,
    summary="List compliance checks",
    description="Retrieve a paginated list of all compliance checks.",
)
async def list_checks(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    contract_id: Optional[int] = Query(None, description="Filter by contract ID"),
    invoice_id: Optional[int] = Query(None, description="Filter by invoice ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    compliance_service = ComplianceService(db)
    checks, total = await compliance_service.get_checks(
        page=page, page_size=page_size, contract_id=contract_id, invoice_id=invoice_id
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return ComplianceListResponse(
        checks=checks,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
