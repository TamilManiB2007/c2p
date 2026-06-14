import os
import uuid
from pathlib import Path
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi import UploadFile, HTTPException, status

from app.core.config import get_settings
from app.models.contract import Contract, ContractStatus
from app.schemas.contract import ContractCreate, ContractUpdate

settings = get_settings()

UPLOAD_DIR = Path(settings.UPLOAD_DIR)
MAX_FILE_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_MIME_TYPES = {"application/pdf"}
ALLOWED_EXTENSIONS = {".pdf"}


class ContractService:
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

    async def _save_file(self, file: UploadFile, user_id: int) -> tuple[str, str, int]:
        """
        Read, validate size, and persist the uploaded file to disk.

        Returns:
            Tuple of (absolute_file_path, unique_filename, file_size_in_bytes)
        """
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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
        file_path = UPLOAD_DIR / unique_filename

        with open(file_path, "wb") as f:
            f.write(content)

        return str(file_path), unique_filename, len(content)

    async def upload_contract(
        self,
        file: UploadFile,
        contract_data: ContractCreate,
        user_id: int,
    ) -> Contract:
        """
        Validate, store the PDF file, and persist contract metadata to the database.

        Raises:
            HTTPException 400: If file is invalid or contract number already exists.
        """
        self._validate_file(file)
        file_path, file_name, file_size = await self._save_file(file, user_id)

        contract = Contract(
            vendor_name=contract_data.vendor_name,
            contract_number=contract_data.contract_number,
            end_date=contract_data.end_date,
            contract_amount=contract_data.contract_amount,
            file_name=file_name,
            file_path=file_path,
            file_size=file_size,
            mime_type=file.content_type,
            created_by=user_id,
        )

        self.db.add(contract)
        try:
            await self.db.commit()
            await self.db.refresh(contract)
            return contract
        except IntegrityError:
            await self.db.rollback()
            # Clean up the saved file if DB commit fails
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Contract number '{contract_data.contract_number}' already exists",
            )

    async def get_contracts(
        self,
        page: int = 1,
        page_size: int = 20,
        status_filter: ContractStatus | None = None,
        vendor_name: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Contract], int]:
        """
        Retrieve a paginated list of contracts with optional filters.

        Args:
            page: 1-based page number.
            page_size: Number of records per page (max 100).
            status_filter: Filter by contract status.
            vendor_name: Exact-match filter on vendor name.
            search: Case-insensitive partial match on vendor_name or contract_number.

        Returns:
            Tuple of (list_of_contracts, total_count).
        """
        query = select(Contract)

        if status_filter:
            query = query.where(Contract.status == status_filter)

        if vendor_name:
            query = query.where(Contract.vendor_name == vendor_name)

        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(
                    Contract.vendor_name.ilike(pattern),
                    Contract.contract_number.ilike(pattern),
                )
            )

        # Count total before pagination
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Apply ordering and pagination
        query = query.order_by(Contract.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        contracts = list(result.scalars().all())

        return contracts, total

    async def get_contract_by_id(self, contract_id: int) -> Contract | None:
        """Retrieve a single contract by its primary key."""
        result = await self.db.execute(
            select(Contract).where(Contract.id == contract_id)
        )
        return result.scalar_one_or_none()

    async def get_contract_file_path(self, contract_id: int) -> tuple[str, str] | None:
        """
        Return (file_path, original_file_name) for a contract, or None if not found.
        Used by the download endpoint.
        """
        contract = await self.get_contract_by_id(contract_id)
        if not contract:
            return None
        return contract.file_path, contract.file_name

    async def update_contract(
        self, contract_id: int, contract_data: ContractUpdate
    ) -> Contract | None:
        """
        Partially update contract metadata (vendor_name, contract_number, status).

        Raises:
            HTTPException 409: If the new contract_number already exists on another record.
        """
        contract = await self.get_contract_by_id(contract_id)
        if not contract:
            return None

        update_data = contract_data.model_dump(exclude_unset=True)

        # Guard against duplicate contract_number on a different record
        if "contract_number" in update_data:
            existing = await self.db.execute(
                select(Contract).where(
                    Contract.contract_number == update_data["contract_number"],
                    Contract.id != contract_id,
                )
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Contract number '{update_data['contract_number']}' already exists",
                )

        for field, value in update_data.items():
            setattr(contract, field, value)

        await self.db.commit()
        await self.db.refresh(contract)
        return contract

    async def delete_contract(self, contract_id: int) -> bool:
        """
        Delete a contract record and remove the associated PDF from disk.

        Returns:
            True if the contract was found and deleted, False otherwise.
        """
        contract = await self.get_contract_by_id(contract_id)
        if not contract:
            return False

        # Remove the file from disk before deleting the DB record
        if contract.file_path and os.path.exists(contract.file_path):
            try:
                os.remove(contract.file_path)
            except OSError:
                # Log but don't block the DB delete if file removal fails
                pass

        await self.db.delete(contract)
        await self.db.commit()
        return True