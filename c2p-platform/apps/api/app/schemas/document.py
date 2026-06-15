from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List, Optional


class ExtractionResult(BaseModel):
    fields: Dict[str, Any] = Field(..., description="Parsed metadata fields")
    confidence: Dict[str, float] = Field(..., description="Field level confidence scores (0.0 to 1.0)")
    warnings: List[str] = Field(..., description="Any warnings identified during parsing")
    raw_text: str = Field(..., description="Full raw text extracted from PDF")
    doc_type: str = Field(..., description="Type of document: 'contract' or 'invoice'")
    temp_file_id: str = Field(..., description="Temporary UUID filename for PDF preview")


class DocumentConfirmRequest(BaseModel):
    temp_file_id: str = Field(..., description="The temporary UUID filename of the PDF")
    doc_type: str = Field(..., description="Type of document: 'contract' or 'invoice'")
    fields: Dict[str, Any] = Field(..., description="User verified and edited fields")


class DocumentExtractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    doc_type: str
    status: str
    extracted_data: Dict[str, Any]
    confidence_scores: Dict[str, float]
    warnings: List[str]
    created_at: datetime
