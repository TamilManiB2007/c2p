import io
import os
import uuid
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch
from httpx import AsyncClient
from pathlib import Path
from decimal import Decimal
from datetime import date, datetime

from app.core.security import create_access_token
from app.models.user import User
from app.models.document import DocumentExtraction
from app.models.contract import Contract
from app.models.invoice import Invoice
from app.services.document_parser import DocumentParser
from app.api.v1.documents.router import TEMP_DIR


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------

def _make_pdf_bytes(content: bytes = b"PDF content") -> bytes:
    """Minimal fake PDF bytes that pass extension/mime checks."""
    return b"%PDF-1.4\n" + content


def _auth_headers(user_id: int, email: str) -> dict:
    token = create_access_token(data={"user_id": user_id, "email": email})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def auth_user(db_session) -> tuple[User, dict]:
    """Create a unique test user and return (user, auth_headers)."""
    unique_email = f"docs-{uuid.uuid4().hex[:8]}@example.com"
    from app.core.security import get_password_hash
    user = User(
        email=unique_email,
        full_name="Document Tester",
        hashed_password=get_password_hash("securepassword"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    headers = _auth_headers(user.id, user.email)
    return user, headers


@pytest_asyncio.fixture
def clean_temp_dir():
    """Ensure uploads/temp is clean before and after tests."""
    if TEMP_DIR.exists():
        import shutil
        shutil.rmtree(str(TEMP_DIR), ignore_errors=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    yield
    if TEMP_DIR.exists():
        import shutil
        shutil.rmtree(str(TEMP_DIR), ignore_errors=True)


# ---------------------------------------------------------------------------
# DocumentParser Service Tests
# ---------------------------------------------------------------------------

class TestDocumentParserService:
    def test_parse_contract_explicit(self):
        text = """
        CONTRACT FOR SERVICES
        This Agreement is made by and between:
        Supplier: Acme Corporation Inc.
        Contract Amount $1,250,000.50
        Start Date: 2026-06-15
        End Date: 2027-06-15
        Contract Number: CTR-98765-A
        """
        fields, confidence, warnings = DocumentParser.parse_contract(text)
        
        assert fields["vendor_name"] == "Acme Corporation Inc"
        assert fields["contract_number"] == "CTR-98765-A"
        assert fields["contract_amount"] == 1250000.50
        assert fields["start_date"] == "2026-06-15"
        assert fields["end_date"] == "2027-06-15"
        assert confidence["vendor_name"] >= 0.8
        assert confidence["contract_number"] >= 0.8
        assert confidence["contract_amount"] >= 0.8
        assert len(warnings) == 0

    def test_parse_contract_fallback(self):
        text = """
        Wayne Enterprises LLC
        Reference CTR-1002
        The total value is $500,000
        Let's do a secondary date check:
        First date: 2026-01-01
        Second date: 2026-12-31
        """
        # start_date is not found, end_date will fall back to second date if len >= 2 and start_date is set.
        # Wait, if start_date is None, let's see how start_date and end_date behavior works:
        fields, confidence, warnings = DocumentParser.parse_contract(text)
        
        assert fields["vendor_name"] == "Wayne Enterprises LLC"
        assert fields["contract_number"] == "CTR-1002"
        assert fields["contract_amount"] == 500000.00
        assert fields["start_date"] is None
        assert fields["end_date"] is None
        assert confidence["vendor_name"] == 0.5
        assert confidence["contract_number"] == 0.6
        assert len(warnings) > 0
    def test_parse_invoice_explicit(self):
        text = """
        Invoice Date: May 12, 2026
        Biller Name: Global Logistics Corp
        Total Amount $4,500.00
        Invoice Number: INV-2026-0045
        """
        fields, confidence, warnings = DocumentParser.parse_invoice(text)
        
        assert fields["vendor_name"] == "Global Logistics Corp"
        assert fields["invoice_number"] == "INV-2026-0045"
        assert fields["invoice_date"] == "2026-05-12"
        assert fields["invoice_amount"] == 4500.00
        assert confidence["vendor_name"] >= 0.8
        assert confidence["invoice_number"] >= 0.8
        assert confidence["invoice_date"] >= 0.8
        assert confidence["invoice_amount"] >= 0.8
        assert len(warnings) == 0

    def test_parse_invoice_fallback(self):
        text = """
        Cyberdyne Systems Inc
        INV99485
        Date of service: 12-05-2026
        Balance Due: $750.25
        """
        fields, confidence, warnings = DocumentParser.parse_invoice(text)
        
        assert fields["vendor_name"] == "Cyberdyne Systems Inc"
        assert fields["invoice_number"] == "INV99485"
        assert fields["invoice_date"] == "2026-12-05"  # Fallback parse_date DD/MM/YYYY
        assert fields["invoice_amount"] == 750.25
        assert confidence["vendor_name"] == 0.5
        assert confidence["invoice_number"] == 0.6  # Fallback INV search confidence is 0.6
        assert confidence["invoice_amount"] == 0.5
        assert len(warnings) > 0

    def test_extract_text_pdfplumber(self, tmp_path):
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(_make_pdf_bytes())

        # Mock pdfplumber
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Extracted text via pdfplumber"
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]

        with patch("pdfplumber.open", return_value=MagicMock(__enter__=MagicMock(return_value=mock_pdf))):
            text = DocumentParser.extract_text(str(pdf_file))
            assert text == "Extracted text via pdfplumber"

    def test_extract_text_pymupdf_fallback(self, tmp_path):
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(_make_pdf_bytes())

        # Mock pdfplumber failure, PyMuPDF success
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Extracted text via PyMuPDF fallback"
        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = [mock_page]

        with patch("pdfplumber.open", side_effect=Exception("Failed open")), \
             patch("fitz.open", return_value=mock_doc):
            text = DocumentParser.extract_text(str(pdf_file))
            assert text == "Extracted text via PyMuPDF fallback"


# ---------------------------------------------------------------------------
# API Route Tests
# ---------------------------------------------------------------------------

class TestDocumentAPI:
    async def test_extract_requires_auth(self, client: AsyncClient):
        form_data = {"doc_type": "contract"}
        files = {"file": ("contract.pdf", _make_pdf_bytes(), "application/pdf")}
        resp = await client.post("/api/v1/documents/extract", data=form_data, files=files)
        assert resp.status_code == 401

    async def test_extract_invalid_doc_type(self, client: AsyncClient, auth_user):
        _, headers = auth_user
        form_data = {"doc_type": "invalid_type"}
        files = {"file": ("contract.pdf", _make_pdf_bytes(), "application/pdf")}
        resp = await client.post("/api/v1/documents/extract", data=form_data, files=files, headers=headers)
        assert resp.status_code == 400
        assert "doc_type must be" in resp.json()["detail"]

    async def test_extract_non_pdf_rejected(self, client: AsyncClient, auth_user):
        _, headers = auth_user
        form_data = {"doc_type": "contract"}
        files = {"file": ("text.txt", b"plain text", "text/plain")}
        resp = await client.post("/api/v1/documents/extract", data=form_data, files=files, headers=headers)
        assert resp.status_code == 400
        assert "Only PDF documents" in resp.json()["detail"]

    async def test_extract_contract_success(self, client: AsyncClient, auth_user, clean_temp_dir):
        _, headers = auth_user
        form_data = {"doc_type": "contract"}
        files = {"file": ("contract.pdf", _make_pdf_bytes(), "application/pdf")}

        dummy_text = "Vendor Name: Acme Corp\nContract Amount: $50000\nContract Number: CTR-2026-X"
        with patch("app.services.document_parser.DocumentParser.extract_text", return_value=dummy_text):
            resp = await client.post("/api/v1/documents/extract", data=form_data, files=files, headers=headers)

        assert resp.status_code == 201
        res = resp.json()
        assert res["doc_type"] == "contract"
        assert res["fields"]["vendor_name"] == "Acme Corp"
        assert res["fields"]["contract_number"] == "CTR-2026-X"
        assert res["fields"]["contract_amount"] == 50000.00
        assert res["temp_file_id"].endswith(".pdf")
        assert (TEMP_DIR / res["temp_file_id"]).exists()

    async def test_extract_invoice_success(self, client: AsyncClient, auth_user, clean_temp_dir):
        _, headers = auth_user
        form_data = {"doc_type": "invoice"}
        files = {"file": ("invoice.pdf", _make_pdf_bytes(), "application/pdf")}

        dummy_text = "Vendor: Biller LLC\nInvoice Date: 2026-06-15\nTotal Amount: $1250\nInvoice: INV-101"
        with patch("app.services.document_parser.DocumentParser.extract_text", return_value=dummy_text):
            resp = await client.post("/api/v1/documents/extract", data=form_data, files=files, headers=headers)

        assert resp.status_code == 201
        res = resp.json()
        assert res["doc_type"] == "invoice"
        assert res["fields"]["vendor_name"] == "Biller LLC"
        assert res["fields"]["invoice_number"] == "INV-101"
        assert res["fields"]["invoice_date"] == "2026-06-15"
        assert res["fields"]["invoice_amount"] == 1250.00
        assert res["temp_file_id"].endswith(".pdf")

    async def test_get_temp_file_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/documents/temp/nonexistent.pdf")
        assert resp.status_code == 404

    async def test_get_temp_file_success(self, client: AsyncClient, clean_temp_dir):
        temp_file_id = "test-preview.pdf"
        file_path = TEMP_DIR / temp_file_id
        file_path.write_bytes(_make_pdf_bytes(b"Testing PDF streaming"))

        resp = await client.get(f"/api/v1/documents/temp/{temp_file_id}")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert b"Testing PDF streaming" in resp.content

    async def test_confirm_requires_auth(self, client: AsyncClient):
        confirm_data = {
            "temp_file_id": "dummy.pdf",
            "doc_type": "contract",
            "fields": {}
        }
        resp = await client.post("/api/v1/documents/confirm", json=confirm_data)
        assert resp.status_code == 401

    async def test_confirm_contract_success(self, client: AsyncClient, auth_user, clean_temp_dir, db_session, monkeypatch):
        # Patch contract uploads directory to use python tmp dir
        monkeypatch.setattr("app.api.v1.documents.router.shutil.move", lambda src, dst: open(dst, "wb").write(open(src, "rb").read()))

        user, headers = auth_user
        
        # 1. First run extract to populate database and create temp file
        form_data = {"doc_type": "contract"}
        files = {"file": ("contract.pdf", _make_pdf_bytes(b"Test bytes"), "application/pdf")}
        dummy_text = "Vendor Name: Test Vendor Inc\nContract Number: CTR-CONF-001\nContract Amount: $99000\nEnd Date: 2026-12-31"
        
        with patch("app.services.document_parser.DocumentParser.extract_text", return_value=dummy_text):
            extract_resp = await client.post("/api/v1/documents/extract", data=form_data, files=files, headers=headers)
        
        assert extract_resp.status_code == 201
        temp_file_id = extract_resp.json()["temp_file_id"]

        # 2. Confirm the extraction
        confirm_data = {
            "temp_file_id": temp_file_id,
            "doc_type": "contract",
            "fields": {
                "vendor_name": "Test Vendor Inc",
                "contract_number": "CTR-CONF-001",
                "contract_amount": "99000.00",
                "end_date": "2026-12-31"
            }
        }
        
        confirm_resp = await client.post("/api/v1/documents/confirm", json=confirm_data, headers=headers)
        assert confirm_resp.status_code == 201
        assert "confirmed" in confirm_resp.json()["message"]

        # 3. Check database states
        from sqlalchemy import select
        # Verify contract created
        q_contract = select(Contract).where(Contract.contract_number == "CTR-CONF-001")
        contract = (await db_session.execute(q_contract)).scalar_one_or_none()
        assert contract is not None
        assert contract.vendor_name == "Test Vendor Inc"
        assert contract.contract_amount == Decimal("99000.00")
        assert contract.end_date == date(2026, 12, 31)

        # Verify extraction run updated
        q_extraction = select(DocumentExtraction).where(DocumentExtraction.temp_file_name == temp_file_id)
        extraction = (await db_session.execute(q_extraction)).scalar_one_or_none()
        assert extraction is not None
        assert extraction.status == "confirmed"

    async def test_confirm_invoice_success(self, client: AsyncClient, auth_user, clean_temp_dir, db_session, monkeypatch):
        monkeypatch.setattr("app.api.v1.documents.router.shutil.move", lambda src, dst: open(dst, "wb").write(open(src, "rb").read()))

        user, headers = auth_user
        
        # 1. Run extract to populate database and create temp file
        form_data = {"doc_type": "invoice"}
        files = {"file": ("invoice.pdf", _make_pdf_bytes(b"Test bytes invoice"), "application/pdf")}
        dummy_text = "Vendor Name: Super Biller\nInvoice Date: 2026-06-15\nInvoice Amount: $150.75\nInvoice Number: INV-CONF-002"
        
        with patch("app.services.document_parser.DocumentParser.extract_text", return_value=dummy_text):
            extract_resp = await client.post("/api/v1/documents/extract", data=form_data, files=files, headers=headers)
        
        assert extract_resp.status_code == 201
        temp_file_id = extract_resp.json()["temp_file_id"]

        # 2. Confirm the extraction
        confirm_data = {
            "temp_file_id": temp_file_id,
            "doc_type": "invoice",
            "fields": {
                "vendor_name": "Super Biller",
                "invoice_number": "INV-CONF-002",
                "invoice_date": "2026-06-15",
                "invoice_amount": "150.75"
            }
        }
        
        confirm_resp = await client.post("/api/v1/documents/confirm", json=confirm_data, headers=headers)
        assert confirm_resp.status_code == 201
        assert "confirmed" in confirm_resp.json()["message"]

        # 3. Check database states
        from sqlalchemy import select
        q_invoice = select(Invoice).where(Invoice.invoice_number == "INV-CONF-002")
        invoice = (await db_session.execute(q_invoice)).scalar_one_or_none()
        assert invoice is not None
        assert invoice.vendor_name == "Super Biller"
        assert invoice.total_amount == Decimal("150.75")
        assert invoice.invoice_date == date(2026, 6, 15)

    async def test_get_history_success(self, client: AsyncClient, auth_user, db_session):
        user, headers = auth_user

        # Create dummy extractions in DB
        e1 = DocumentExtraction(
            file_name="c1.pdf",
            temp_file_name="t1.pdf",
            doc_type="contract",
            status="pending",
            extracted_data={},
            confidence_scores={},
            warnings=[],
            raw_text="Contract 1",
            created_by=user.id
        )
        db_session.add(e1)
        await db_session.commit()

        resp = await client.get("/api/v1/documents/history", headers=headers)
        assert resp.status_code == 200
        history = resp.json()
        assert len(history) >= 1
        assert history[0]["file_name"] == "c1.pdf"
        assert history[0]["doc_type"] == "contract"
