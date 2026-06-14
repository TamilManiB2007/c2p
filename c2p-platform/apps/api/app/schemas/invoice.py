from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from typing import List

from app.models.invoice import InvoiceStatus


class InvoiceBase(BaseModel):
    invoice_number: str = Field(..., min_length=1, max_length=100, examples=["INV-2024-001"])
    vendor_name: str = Field(..., min_length=1, max_length=255, examples=["Acme Corp"])
    invoice_date: date = Field(..., examples=["2024-01-15"])
    total_amount: Decimal = Field(..., ge=0, examples=[1500.50])


class InvoiceCreate(InvoiceBase):
    """Schema used when creating a new invoice (multipart form data)."""
    pass


class InvoiceResponse(InvoiceBase):
    """Full invoice representation returned by the API."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    file_path: str
    status: InvoiceStatus
    uploaded_by: int
    created_at: datetime
    updated_at: datetime


class InvoiceListResponse(BaseModel):
    """Paginated list of invoices."""
    invoices: List[InvoiceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class InvoiceUploadResponse(BaseModel):
    """Response returned after a successful invoice upload."""
    message: str
    invoice: InvoiceResponse


class InvoiceDeleteResponse(BaseModel):
    """Response returned after a successful invoice deletion."""
    message: str
    invoice_id: int
