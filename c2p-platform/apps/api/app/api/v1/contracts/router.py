"""
Contracts API Router — Phase 2: Contract Management Module

Endpoints:
  POST   /contracts/upload          — Upload a contract PDF
  GET    /contracts/                 — List contracts (paginated, filterable)
  GET    /contracts/{id}             — Get contract details
  GET    /contracts/{id}/download    — Download contract PDF
  PATCH  /contracts/{id}             — Update contract metadata
  DELETE /contracts/{id}             — Delete contract

All endpoints require a valid JWT bearer token.
"""
from datetime import date
from decimal import Decimal
import os
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db_session
from app.api.deps import get_current_active_user
from app.models.contract import ContractStatus
from app.models.user import User
from app.schemas.contract import (
    ContractUpdate,
    ContractResponse,
    ContractListResponse,
    ContractUploadResponse,
    ContractDeleteResponse,
)
from app.services.contract_service import ContractService

router = APIRouter(prefix="/contracts", tags=["Contracts"])


# ---------------------------------------------------------------------------
# POST /contracts/upload
# ---------------------------------------------------------------------------
@router.post(
    "/upload",
    response_model=ContractUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a contract PDF",
    description=(
        "Upload a PDF contract file along with vendor metadata. "
        "Accepts multipart/form-data. PDF only, max 20 MB."
    ),
)
async def upload_contract(
    file: UploadFile = File(..., description="PDF contract file (max 20 MB)"),
    vendor_name: str = Form(..., min_length=1, max_length=255, description="Vendor / supplier name"),
    contract_number: str = Form(..., min_length=1, max_length=100, description="Unique contract reference number"),
    end_date: Optional[date] = Form(None, description="Contract end date (YYYY-MM-DD)"),
    contract_amount: Optional[Decimal] = Form(None, ge=0, description="Total contract amount limit"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    from app.schemas.contract import ContractCreate  # local import to avoid circular
    contract_service = ContractService(db)
    contract_data = ContractCreate(
        vendor_name=vendor_name,
        contract_number=contract_number,
        end_date=end_date,
        contract_amount=contract_amount,
    )
    contract = await contract_service.upload_contract(file, contract_data, current_user.id)
    return ContractUploadResponse(
        message="Contract uploaded successfully",
        contract=contract,
    )


# ---------------------------------------------------------------------------
# GET /contracts/
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=ContractListResponse,
    summary="List contracts",
    description="Retrieve a paginated list of contracts. Supports filtering by status, vendor name, or a free-text search.",
)
async def list_contracts(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of results per page"),
    status_filter: Optional[ContractStatus] = Query(None, alias="status", description="Filter by contract status"),
    vendor_name: Optional[str] = Query(None, description="Exact vendor name filter"),
    search: Optional[str] = Query(None, description="Free-text search across vendor name and contract number"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    contract_service = ContractService(db)
    contracts, total = await contract_service.get_contracts(
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        vendor_name=vendor_name,
        search=search,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return ContractListResponse(
        contracts=contracts,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ---------------------------------------------------------------------------
# GET /contracts/{contract_id}
# ---------------------------------------------------------------------------
@router.get(
    "/{contract_id}",
    response_model=ContractResponse,
    summary="Get contract details",
    description="Retrieve full metadata for a single contract by its ID.",
)
async def get_contract(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    contract_service = ContractService(db)
    contract = await contract_service.get_contract_by_id(contract_id)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract with id={contract_id} not found",
        )
    return contract


# ---------------------------------------------------------------------------
# GET /contracts/{contract_id}/download
# ---------------------------------------------------------------------------
@router.get(
    "/{contract_id}/download",
    summary="Download contract PDF",
    description="Stream the original PDF file associated with the contract.",
    response_class=FileResponse,
)
async def download_contract(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    contract_service = ContractService(db)
    result = await contract_service.get_contract_file_path(contract_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract with id={contract_id} not found",
        )

    file_path, file_name = result

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract file not found on disk. It may have been removed.",
        )

    # Return the stored file under its original name
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=f"contract_{contract_id}.pdf",
        headers={"Content-Disposition": f'attachment; filename="contract_{contract_id}.pdf"'},
    )


# ---------------------------------------------------------------------------
# PATCH /contracts/{contract_id}
# ---------------------------------------------------------------------------
@router.patch(
    "/{contract_id}",
    response_model=ContractResponse,
    summary="Update contract metadata",
    description="Partially update vendor_name, contract_number, or status of a contract.",
)
async def update_contract(
    contract_id: int,
    contract_data: ContractUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    contract_service = ContractService(db)
    contract = await contract_service.update_contract(contract_id, contract_data)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract with id={contract_id} not found",
        )
    return contract


# ---------------------------------------------------------------------------
# DELETE /contracts/{contract_id}
# ---------------------------------------------------------------------------
@router.delete(
    "/{contract_id}",
    response_model=ContractDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a contract",
    description="Permanently delete a contract record and its associated PDF file from disk.",
)
async def delete_contract(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    contract_service = ContractService(db)
    deleted = await contract_service.delete_contract(contract_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract with id={contract_id} not found",
        )
    return ContractDeleteResponse(
        message="Contract deleted successfully",
        contract_id=contract_id,
    )