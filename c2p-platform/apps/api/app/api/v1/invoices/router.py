"""
Invoices API Router — Phase 3: Invoice Management Module

Endpoints:
  POST   /invoices/upload          — Upload an invoice PDF
  GET    /invoices/                 — List invoices (paginated, filterable)
  GET    /invoices/{id}             — Get invoice details
  GET    /invoices/{id}/download    — Download invoice PDF
  DELETE /invoices/{id}             — Delete invoice

All endpoints require a valid JWT bearer token.
"""
from datetime import date
from decimal import Decimal
import os
from pathlib import Path
from typing import Optional

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

from app.core.database import get_db_session
from app.api.deps import get_current_active_user
from app.models.invoice import InvoiceStatus
from app.models.user import User
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceResponse,
    InvoiceListResponse,
    InvoiceUploadResponse,
    InvoiceDeleteResponse,
)
from app.services.invoice_service import InvoiceService

router = APIRouter(prefix="/invoices", tags=["Invoices"])


# ---------------------------------------------------------------------------
# POST /invoices/upload
# ---------------------------------------------------------------------------
@router.post(
    "/upload",
    response_model=InvoiceUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an invoice PDF",
    description=(
        "Upload a PDF invoice file along with invoice metadata. "
        "Accepts multipart/form-data. PDF only, max 20 MB."
    ),
)
async def upload_invoice(
    file: UploadFile = File(..., description="PDF invoice file (max 20 MB)"),
    invoice_number: str = Form(..., min_length=1, max_length=100, description="Unique invoice reference number"),
    vendor_name: str = Form(..., min_length=1, max_length=255, description="Vendor / supplier name"),
    invoice_date: date = Form(..., description="Invoice date (YYYY-MM-DD)"),
    total_amount: Decimal = Form(..., ge=0, description="Total amount of the invoice"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    invoice_service = InvoiceService(db)
    invoice_data = InvoiceCreate(
        invoice_number=invoice_number,
        vendor_name=vendor_name,
        invoice_date=invoice_date,
        total_amount=total_amount,
    )
    invoice = await invoice_service.upload_invoice(file, invoice_data, current_user.id)
    return InvoiceUploadResponse(
        message="Invoice uploaded successfully",
        invoice=invoice,
    )


# ---------------------------------------------------------------------------
# GET /invoices/
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=InvoiceListResponse,
    summary="List invoices",
    description="Retrieve a paginated list of invoices. Supports filtering by status, vendor name, or a free-text search.",
)
async def list_invoices(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of results per page"),
    status_filter: Optional[InvoiceStatus] = Query(None, alias="status", description="Filter by invoice status"),
    vendor_name: Optional[str] = Query(None, description="Exact vendor name filter"),
    search: Optional[str] = Query(None, description="Free-text search across vendor name and invoice number"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    invoice_service = InvoiceService(db)
    invoices, total = await invoice_service.get_invoices(
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        vendor_name=vendor_name,
        search=search,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return InvoiceListResponse(
        invoices=invoices,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ---------------------------------------------------------------------------
# GET /invoices/{invoice_id}
# ---------------------------------------------------------------------------
@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Get invoice details",
    description="Retrieve full metadata for a single invoice by its ID.",
)
async def get_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    invoice_service = InvoiceService(db)
    invoice = await invoice_service.get_invoice_by_id(invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id={invoice_id} not found",
        )
    return invoice


# ---------------------------------------------------------------------------
# GET /invoices/{invoice_id}/download
# ---------------------------------------------------------------------------
@router.get(
    "/{invoice_id}/download",
    summary="Download invoice PDF",
    description="Stream the original PDF file associated with the invoice.",
    response_class=FileResponse,
)
async def download_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    invoice_service = InvoiceService(db)
    result = await invoice_service.get_invoice_file_path(invoice_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id={invoice_id} not found",
        )

    file_path, file_name = result

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice file not found on disk. It may have been removed.",
        )

    # Return the stored file under its original name
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=f"invoice_{invoice_id}.pdf",
        headers={"Content-Disposition": f'attachment; filename="invoice_{invoice_id}.pdf"'},
    )


# ---------------------------------------------------------------------------
# DELETE /invoices/{invoice_id}
# ---------------------------------------------------------------------------
@router.delete(
    "/{invoice_id}",
    response_model=InvoiceDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete an invoice",
    description="Permanently delete an invoice record and its associated PDF file from disk.",
)
async def delete_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    invoice_service = InvoiceService(db)
    deleted = await invoice_service.delete_invoice(invoice_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id={invoice_id} not found",
        )
    return InvoiceDeleteResponse(
        message="Invoice deleted successfully",
        invoice_id=invoice_id,
    )
