from datetime import datetime, date, timezone
from sqlalchemy import DateTime, Date, Numeric, Enum, ForeignKey, String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
import enum

from app.core.database import Base
from app.models.user import User


class ContractStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vendor_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contract_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    upload_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus), default=ContractStatus.UPLOADED, nullable=False
    )
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    contract_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    creator: Mapped[User] = relationship("User", backref="contracts")

    def __repr__(self) -> str:
        return f"<Contract(id={self.id}, contract_number={self.contract_number}, vendor={self.vendor_name})>"