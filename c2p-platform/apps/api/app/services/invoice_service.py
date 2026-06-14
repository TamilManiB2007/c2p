import os
import uuid
from pathlib import Path
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi import UploadFile, HTTPException, status

from app.core.config import get_settings
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.invoice import InvoiceCreate

settings = get_settings()

INVOICES_UPLOAD_DIR = Path(settings.INVOICES_UPLOAD_DIR)
MAX_FILE_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_MIME_TYPES = {"application/pdf"}
ALLOWED_EXTENSIONS = {".pdf"}


class InvoiceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _validate_file(self, file: UploadFile) -> None:
        """Validate that the uploaded file is a PDF and within size constraints."""
        # Validate MIME type
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed. Received content type: "
                       f"{file.content_type}",
            )

        # Validate file extension as a secondary check
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File name is required",
            )

        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file extension '{ext}'. Only .pdf files are allowed",
            )

    async def _save_file(self, file: UploadFile) -> tuple[str, str, int]:
        """
        Read, validate size, and persist the uploaded file to disk.

        Returns:
            Tuple of (absolute_file_path, unique_filename, file_size_in_bytes)
        """
        INVOICES_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"File size {len(content) / (1024 * 1024):.1f}MB exceeds "
                    f"the {settings.MAX_FILE_SIZE_MB}MB limit"
                ),
            )

        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty",
            )

        file_ext = Path(file.filename).suffix.lower()
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = INVOICES_UPLOAD_DIR / unique_filename

        with open(file_path, "wb") as f:
            f.write(content)

        return str(file_path), unique_filename, len(content)

    async def upload_invoice(
        self,
        file: UploadFile,
        invoice_data: InvoiceCreate,
        user_id: int,
    ) -> Invoice:
        """
        Validate, store the PDF file, and persist invoice metadata to the database.

        Raises:
            HTTPException 400: If file is invalid.
            HTTPException 409: If invoice number already exists.
        """
        self._validate_file(file)
        file_path, file_name, file_size = await self._save_file(file)

        invoice = Invoice(
            invoice_number=invoice_data.invoice_number,
            vendor_name=invoice_data.vendor_name,
            invoice_date=invoice_data.invoice_date,
            total_amount=invoice_data.total_amount,
            file_name=file_name,
            file_path=file_path,
            status=InvoiceStatus.UPLOADED,
            uploaded_by=user_id,
        )

        self.db.add(invoice)
        try:
            await self.db.commit()
            await self.db.refresh(invoice)
            return invoice
        except IntegrityError:
            await self.db.rollback()
            # Clean up the saved file if DB commit fails
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Invoice number '{invoice_data.invoice_number}' already exists",
            )

    async def get_invoices(
        self,
        page: int = 1,
        page_size: int = 20,
        status_filter: InvoiceStatus | None = None,
        vendor_name: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Invoice], int]:
        """
        Retrieve a paginated list of invoices with optional filters.

        Args:
            page: 1-based page number.
            page_size: Number of records per page (max 100).
            status_filter: Filter by invoice status.
            vendor_name: Exact-match filter on vendor name.
            search: Case-insensitive partial match on vendor_name or invoice_number.

        Returns:
            Tuple of (list_of_invoices, total_count).
        """
        query = select(Invoice)

        if status_filter:
            query = query.where(Invoice.status == status_filter)

        if vendor_name:
            query = query.where(Invoice.vendor_name == vendor_name)

        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(
                    Invoice.vendor_name.ilike(pattern),
                    Invoice.invoice_number.ilike(pattern),
                )
            )

        # Count total before pagination
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Apply ordering and pagination
        query = query.order_by(Invoice.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        invoices = list(result.scalars().all())

        return invoices, total

    async def get_invoice_by_id(self, invoice_id: int) -> Invoice | None:
        """Retrieve a single invoice by its primary key."""
        result = await self.db.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        return result.scalar_one_or_none()

    async def get_invoice_file_path(self, invoice_id: int) -> tuple[str, str] | None:
        """
        Return (file_path, original_file_name) for an invoice, or None if not found.
        Used by the download endpoint.
        """
        invoice = await self.get_invoice_by_id(invoice_id)
        if not invoice:
            return None
        return invoice.file_path, invoice.file_name

    async def delete_invoice(self, invoice_id: int) -> bool:
        """
        Delete an invoice record and remove the associated PDF from disk.

        Returns:
            True if the invoice was found and deleted, False otherwise.
        """
        invoice = await self.get_invoice_by_id(invoice_id)
        if not invoice:
            return False

        # Remove the file from disk before deleting the DB record
        if invoice.file_path and os.path.exists(invoice.file_path):
            try:
                os.remove(invoice.file_path)
            except OSError:
                # Log but don't block the DB delete if file removal fails
                pass

        await self.db.delete(invoice)
        await self.db.commit()
        return True
