from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

from app.models.contract import ContractStatus


class ContractBase(BaseModel):
    vendor_name: str = Field(..., min_length=1, max_length=255, examples=["Acme Corp"])
    contract_number: str = Field(..., min_length=1, max_length=100, examples=["CTR-2024-001"])
    end_date: Optional[date] = Field(None, description="Contract end date (YYYY-MM-DD)", examples=["2024-12-31"])
    contract_amount: Optional[Decimal] = Field(None, ge=0, description="Total contract amount limit", examples=[50000.00])


class ContractCreate(ContractBase):
    """Schema used when creating a new contract (multipart form data)."""
    pass


class ContractUpdate(BaseModel):
    """Schema for partial updates to contract metadata."""
    vendor_name: Optional[str] = Field(None, min_length=1, max_length=255)
    contract_number: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[ContractStatus] = None
    end_date: Optional[date] = None
    contract_amount: Optional[Decimal] = Field(None, ge=0)


class ContractResponse(ContractBase):
    """Full contract representation returned by the API."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    file_path: str
    file_size: int
    mime_type: str
    upload_date: datetime
    status: ContractStatus
    created_by: int
    created_at: datetime
    updated_at: datetime


class ContractListResponse(BaseModel):
    """Paginated list of contracts."""
    contracts: List[ContractResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ContractUploadResponse(BaseModel):
    """Response returned after a successful contract upload."""
    message: str
    contract: ContractResponse


class ContractDeleteResponse(BaseModel):
    """Response returned after a successful contract deletion."""
    message: str
    contract_id: int