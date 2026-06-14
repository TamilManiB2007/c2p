from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, ForeignKey, String, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
import enum

from app.core.database import Base
from app.models.contract import Contract
from app.models.invoice import Invoice


class ComplianceStatus(str, enum.Enum):
    PASSED = "passed"
    FAILED = "failed"


class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    check_type: Mapped[str] = mapped_column(String(50), default="standard", nullable=False)
    status: Mapped[ComplianceStatus] = mapped_column(
        Enum(ComplianceStatus), default=ComplianceStatus.PASSED, nullable=False
    )
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    contract: Mapped[Contract] = relationship("Contract", backref=backref("compliance_checks", cascade="all, delete-orphan"))
    invoice: Mapped[Invoice] = relationship("Invoice", backref=backref("compliance_checks", cascade="all, delete-orphan"))

    def __repr__(self) -> str:
        return f"<ComplianceCheck(id={self.id}, contract_id={self.contract_id}, invoice_id={self.invoice_id}, status={self.status})>"
