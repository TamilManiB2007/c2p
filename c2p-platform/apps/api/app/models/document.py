from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, String, Text, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Any, Dict, List

from app.core.database import Base
from app.models.user import User


class DocumentExtraction(Base):
    __tablename__ = "document_extractions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    temp_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "contract" or "invoice"
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # "pending", "confirmed", "rejected"
    extracted_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    confidence_scores: Mapped[Dict[str, float]] = mapped_column(JSON, nullable=False)
    warnings: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
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

    creator: Mapped[User] = relationship("User", backref="document_extractions")

    def __repr__(self) -> str:
        return f"<DocumentExtraction(id={self.id}, file={self.file_name}, status={self.status})>"
