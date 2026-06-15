import os
import uuid
import shutil
import datetime
from pathlib import Path
from typing import List
from decimal import Decimal

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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.document import DocumentExtraction
from app.models.contract import Contract
from app.models.invoice import Invoice
from app.schemas.document import (
    ExtractionResult,
    DocumentConfirmRequest,
    DocumentExtractionResponse,
)
from app.services.document_parser import DocumentParser
from app.core.logging import (
    log_upload_start,
    log_extract_start,
    log_extract_complete,
    log_confirm_start,
    log_confirm_complete,
)

router = APIRouter(prefix="/documents", tags=["Document Intelligence"])

TEMP_DIR = Path("uploads/temp")


# ---------------------------------------------------------------------------
# POST /documents/extract
# ---------------------------------------------------------------------------
@router.post(
    "/extract",
    response_model=ExtractionResult,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and extract metadata from PDF",
    description="Deterministically parse metadata fields from a PDF contract or invoice.",
)
async def extract_document(
    file: UploadFile = File(..., description="PDF file to parse"),
    doc_type: str = Form(..., description="Document type: 'contract' or 'invoice'"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    if doc_type not in ("contract", "invoice"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="doc_type must be either 'contract' or 'invoice'",
        )

    log_upload_start(file.filename, doc_type, current_user.id)

    # Validate file type
    if file.content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents are supported for text extraction",
        )

    # Save PDF file temporarily
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    temp_file_id = f"{uuid.uuid4()}.pdf"
    temp_file_path = TEMP_DIR / temp_file_id

    try:
        content = await file.read()
        with open(temp_file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save temporary document file: {str(e)}",
        )

    # Extract text & parse
    try:
        log_extract_start(temp_file_id, doc_type)
        raw_text = DocumentParser.extract_text(str(temp_file_path))
        if doc_type == "contract":
            fields, confidence, warnings = DocumentParser.parse_contract(raw_text)
        else:
            fields, confidence, warnings = DocumentParser.parse_invoice(raw_text)
        log_extract_complete(temp_file_id, doc_type, len(fields), warnings)
    except Exception as e:
        # Clean up temp file in case of failure
        if temp_file_path.exists():
            os.remove(temp_file_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Document parsing failed: {str(e)}",
        )

    # Create document extraction run in database
    db_run = DocumentExtraction(
        file_name=file.filename,
        temp_file_name=temp_file_id,
        doc_type=doc_type,
        status="pending",
        extracted_data=fields,
        confidence_scores=confidence,
        warnings=warnings,
        raw_text=raw_text,
        created_by=current_user.id,
    )
    db.add(db_run)
    await db.commit()

    return ExtractionResult(
        fields=fields,
        confidence=confidence,
        warnings=warnings,
        raw_text=raw_text,
        doc_type=doc_type,
        temp_file_id=temp_file_id,
    )


# ---------------------------------------------------------------------------
# GET /documents/temp/{temp_file_id}
# ---------------------------------------------------------------------------
@router.get(
    "/temp/{temp_file_id}",
    response_class=FileResponse,
    summary="Download temporary document PDF",
    description="Stream the cached PDF file for previewing inside frontend iframes.",
)
async def get_temp_file(
    temp_file_id: str,
):
    temp_file_path = TEMP_DIR / temp_file_id
    if not temp_file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Temporary document file not found",
        )
    return FileResponse(
        path=temp_file_path,
        media_type="application/pdf",
        filename="temp_preview.pdf",
    )


# ---------------------------------------------------------------------------
# POST /documents/confirm
# ---------------------------------------------------------------------------
@router.post(
    "/confirm",
    status_code=status.HTTP_201_CREATED,
    summary="Confirm metadata and save record",
    description="Commit parsed metadata and persist the PDF file permanently to active lists.",
)
async def confirm_document(
    request: DocumentConfirmRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    log_confirm_start(request.temp_file_id, request.doc_type, current_user.id)
    # Fetch extraction run
    q = select(DocumentExtraction).where(
        DocumentExtraction.temp_file_name == request.temp_file_id,
        DocumentExtraction.created_by == current_user.id,
    )
    extraction_run = (await db.execute(q)).scalar_one_or_none()
    if not extraction_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction run not found for the given temp_file_id",
        )

    if extraction_run.status == "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This document has already been confirmed",
        )

    temp_file_path = TEMP_DIR / request.temp_file_id
    if not temp_file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Temporary file not found on disk. It may have expired or been removed.",
        )

    file_size = temp_file_path.stat().st_size

    # Move file to permanent uploads and create active database records
    try:
        if request.doc_type == "contract":
            perm_dir = Path("uploads/contracts")
            perm_dir.mkdir(parents=True, exist_ok=True)
            perm_file_name = f"{uuid.uuid4()}.pdf"
            perm_file_path = perm_dir / perm_file_name

            shutil.move(str(temp_file_path), str(perm_file_path))

            # Normalize values
            amount = request.fields.get("contract_amount")
            if amount is not None and str(amount).strip() != "":
                amount = Decimal(str(amount))
            else:
                amount = None

            end_date = request.fields.get("end_date")
            if end_date and str(end_date).strip() != "":
                end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
            else:
                end_date = None

            start_date = request.fields.get("start_date")
            if start_date and str(start_date).strip() != "":
                # Check for start_date field inside contracts table
                # (The active Contract schema doesn't have start_date columns on the DB, 
                # but let's record it on extraction metadata. DB schema has end_date and amount).
                pass

            contract = Contract(
                vendor_name=request.fields.get("vendor_name", ""),
                contract_number=request.fields.get("contract_number", ""),
                contract_amount=amount,
                end_date=end_date,
                file_name=extraction_run.file_name,
                file_path=str(perm_file_path),
                file_size=file_size,
                mime_type="application/pdf",
                created_by=current_user.id,
            )
            db.add(contract)

        elif request.doc_type == "invoice":
            perm_dir = Path("uploads/invoices")
            perm_dir.mkdir(parents=True, exist_ok=True)
            perm_file_name = f"{uuid.uuid4()}.pdf"
            perm_file_path = perm_dir / perm_file_name

            shutil.move(str(temp_file_path), str(perm_file_path))

            amount = request.fields.get("invoice_amount")
            if amount is not None and str(amount).strip() != "":
                amount = Decimal(str(amount))
            else:
                amount = None

            invoice_date = request.fields.get("invoice_date")
            if invoice_date and str(invoice_date).strip() != "":
                invoice_date = datetime.datetime.strptime(invoice_date, "%Y-%m-%d").date()
            else:
                invoice_date = None

            invoice = Invoice(
                vendor_name=request.fields.get("vendor_name", ""),
                invoice_number=request.fields.get("invoice_number", ""),
                total_amount=amount,
                invoice_date=invoice_date,
                file_name=extraction_run.file_name,
                file_path=str(perm_file_path),
                uploaded_by=current_user.id,
            )
            db.add(invoice)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="doc_type must be either 'contract' or 'invoice'",
            )

        # Update extraction run status
        extraction_run.status = "confirmed"
        extraction_run.extracted_data = request.fields
        await db.commit()

        record_id = None
        if request.doc_type == "contract" and 'contract' in locals():
            record_id = contract.id
        elif request.doc_type == "invoice" and 'invoice' in locals():
            record_id = invoice.id

        log_confirm_complete(request.doc_type, record_id)

        return {"message": f"{request.doc_type.capitalize()} confirmed and created successfully"}
    except Exception as e:
        await db.rollback()
        # Recovery fallback: move file back to temp if it was successfully moved but DB failed
        if 'perm_file_path' in locals() and perm_file_path.exists() and not temp_file_path.exists():
            try:
                shutil.move(str(perm_file_path), str(temp_file_path))
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Confirmation processing failed: {str(e)}",
        )


# ---------------------------------------------------------------------------
# GET /documents/history
# ---------------------------------------------------------------------------
@router.get(
    "/history",
    response_model=List[DocumentExtractionResponse],
    summary="Get document extraction history",
    description="Retrieve lists of all previous text extraction run histories.",
)
async def get_extraction_history(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    q = (
        select(DocumentExtraction)
        .where(DocumentExtraction.created_by == current_user.id)
        .order_by(DocumentExtraction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(q)
    return list(result.scalars().all())
