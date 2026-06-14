from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.contract import Contract
from app.models.invoice import Invoice
from app.models.compliance import ComplianceCheck, ComplianceStatus


class ComplianceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_check(self, contract_id: int, invoice_id: int) -> ComplianceCheck:
        """
        Retrieve contract and invoice, evaluate compliance rules, and record the results.

        Raises:
            HTTPException 404: If contract or invoice is not found.
        """
        # Fetch contract
        contract_result = await self.db.execute(
            select(Contract).where(Contract.id == contract_id)
        )
        contract = contract_result.scalar_one_or_none()
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contract with id={contract_id} not found",
            )

        # Fetch invoice
        invoice_result = await self.db.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        invoice = invoice_result.scalar_one_or_none()
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invoice with id={invoice_id} not found",
            )

        # ── Rule 1: Vendor Mismatch ──────────────────────────────────────────
        vendor_match_passed = contract.vendor_name.strip().lower() == invoice.vendor_name.strip().lower()
        if vendor_match_passed:
            vendor_match_detail = f"Vendor names match: '{contract.vendor_name}'"
        else:
            vendor_match_detail = (
                f"Vendor mismatch: Contract has '{contract.vendor_name}', "
                f"Invoice has '{invoice.vendor_name}'"
            )

        # ── Rule 2: Contract Expired ─────────────────────────────────────────
        if contract.end_date is None:
            expiry_passed = True
            expiry_detail = "Contract has no expiration date defined"
        else:
            expiry_passed = invoice.invoice_date <= contract.end_date
            if expiry_passed:
                expiry_detail = (
                    f"Invoice date {invoice.invoice_date} is within contract validity "
                    f"(ends {contract.end_date})"
                )
            else:
                expiry_detail = (
                    f"Invoice date {invoice.invoice_date} is after contract expiration "
                    f"date {contract.end_date}"
                )

        # ── Rule 3: Invoice Amount Exceeds Contract Amount ───────────────────
        if contract.contract_amount is None:
            amount_passed = True
            amount_detail = "Contract has no amount limit defined"
        else:
            # Cast both to float/Decimal to ensure correct comparison
            amount_passed = float(invoice.total_amount) <= float(contract.contract_amount)
            if amount_passed:
                amount_detail = (
                    f"Invoice amount {invoice.total_amount} is within contract limit "
                    f"{contract.contract_amount}"
                )
            else:
                amount_detail = (
                    f"Invoice amount {invoice.total_amount} exceeds contract limit "
                    f"{contract.contract_amount}"
                )

        # Overall calculation
        overall_passed = vendor_match_passed and expiry_passed and amount_passed
        overall_status = ComplianceStatus.PASSED if overall_passed else ComplianceStatus.FAILED

        details = {
            "vendor_mismatch": {
                "status": "passed" if vendor_match_passed else "failed",
                "detail": vendor_match_detail,
            },
            "contract_expired": {
                "status": "passed" if expiry_passed else "failed",
                "detail": expiry_detail,
            },
            "amount_exceeded": {
                "status": "passed" if amount_passed else "failed",
                "detail": amount_detail,
            },
        }

        check = ComplianceCheck(
            contract_id=contract_id,
            invoice_id=invoice_id,
            check_type="deterministic",
            status=overall_status,
            details=details,
        )

        self.db.add(check)
        await self.db.commit()
        await self.db.refresh(check)
        return check

    async def get_check_by_id(self, check_id: int) -> ComplianceCheck | None:
        """Retrieve a specific compliance check result."""
        result = await self.db.execute(
            select(ComplianceCheck).where(ComplianceCheck.id == check_id)
        )
        return result.scalar_one_or_none()

    async def get_violations(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[ComplianceCheck], int]:
        """Retrieve a paginated list of failed compliance checks (violations)."""
        query = select(ComplianceCheck).where(ComplianceCheck.status == ComplianceStatus.FAILED)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Paginate
        query = query.order_by(ComplianceCheck.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        checks = list(result.scalars().all())

        return checks, total

    async def get_checks(
        self,
        page: int = 1,
        page_size: int = 20,
        contract_id: int | None = None,
        invoice_id: int | None = None,
    ) -> tuple[list[ComplianceCheck], int]:
        """Retrieve a paginated list of all compliance checks."""
        query = select(ComplianceCheck)

        if contract_id:
            query = query.where(ComplianceCheck.contract_id == contract_id)
        if invoice_id:
            query = query.where(ComplianceCheck.invoice_id == invoice_id)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Paginate
        query = query.order_by(ComplianceCheck.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        checks = list(result.scalars().all())

        return checks, total
