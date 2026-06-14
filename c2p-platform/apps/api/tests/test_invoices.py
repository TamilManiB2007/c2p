"""
Tests for Phase 3: Invoice Management Module

Covers:
  - POST /api/v1/invoices/upload
  - GET  /api/v1/invoices/
  - GET  /api/v1/invoices/{id}
  - GET  /api/v1/invoices/{id}/download
  - DELETE /api/v1/invoices/{id}

Security tests:
  - Unauthenticated requests return 401

Validation tests:
  - Non-PDF files rejected (400)
  - Files over 20 MB rejected (400)
  - Duplicate invoice number rejected (409)
"""
import io
import uuid
from decimal import Decimal
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.user import User
from app.core.security import get_password_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pdf_bytes(content: bytes = b"PDF content") -> bytes:
    """Minimal fake PDF bytes that pass extension/mime checks in tests."""
    return b"%PDF-1.4\n" + content


def _auth_headers(user_id: int, email: str) -> dict:
    token = create_access_token(data={"user_id": user_id, "email": email})
    return {"Authorization": f"Bearer {token}"}


def _pdf_upload_form(
    invoice_number: str = "INV-001",
    vendor_name: str = "Acme Corp",
    invoice_date: str = "2024-01-15",
    total_amount: str = "1500.50",
    pdf_bytes: bytes | None = None,
    filename: str = "invoice.pdf",
    content_type: str = "application/pdf",
):
    """Build the multipart form data for invoice upload."""
    if pdf_bytes is None:
        pdf_bytes = _make_pdf_bytes()
    return {
        "files": [("file", (filename, io.BytesIO(pdf_bytes), content_type))],
        "data": {
            "invoice_number": invoice_number,
            "vendor_name": vendor_name,
            "invoice_date": invoice_date,
            "total_amount": total_amount,
        },
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def auth_user(db_session) -> tuple[User, dict]:
    """Create a test user with a unique email and return (user, auth_headers)."""
    unique_email = f"invoices-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=unique_email,
        full_name="Invoice Tester",
        hashed_password=get_password_hash("securepassword"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    headers = _auth_headers(user.id, user.email)
    return user, headers


@pytest_asyncio.fixture
async def uploaded_invoice(client: AsyncClient, auth_user, tmp_path, monkeypatch):
    """
    Upload a single invoice and return the JSON response body.
    Patches INVOICES_UPLOAD_DIR to use a temporary directory for isolation.
    """
    import app.services.invoice_service as is_module
    monkeypatch.setattr(is_module, "INVOICES_UPLOAD_DIR", tmp_path / "invoices")

    _, headers = auth_user
    form = _pdf_upload_form()
    resp = await client.post(
        "/api/v1/invoices/upload",
        headers=headers,
        files=form["files"],
        data=form["data"],
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["invoice"]


# ---------------------------------------------------------------------------
# Security Tests
# ---------------------------------------------------------------------------

class TestInvoiceSecurity:
    async def test_upload_requires_auth(self, client: AsyncClient):
        form = _pdf_upload_form()
        resp = await client.post(
            "/api/v1/invoices/upload",
            files=form["files"],
            data=form["data"],
        )
        assert resp.status_code == 401

    async def test_list_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/invoices/")
        assert resp.status_code == 401

    async def test_get_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/invoices/1")
        assert resp.status_code == 401

    async def test_download_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/invoices/1/download")
        assert resp.status_code == 401

    async def test_delete_requires_auth(self, client: AsyncClient):
        resp = await client.delete("/api/v1/invoices/1")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Upload Tests
# ---------------------------------------------------------------------------

class TestInvoiceUpload:
    async def test_upload_success(self, client: AsyncClient, auth_user, tmp_path, monkeypatch):
        import app.services.invoice_service as is_module
        monkeypatch.setattr(is_module, "INVOICES_UPLOAD_DIR", tmp_path / "invoices")

        _, headers = auth_user
        form = _pdf_upload_form(invoice_number="INV-TEST-999", vendor_name="Test Vendor", invoice_date="2026-06-10", total_amount="123.45")
        resp = await client.post(
            "/api/v1/invoices/upload",
            headers=headers,
            files=form["files"],
            data=form["data"],
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["message"] == "Invoice uploaded successfully"
        invoice = body["invoice"]
        assert invoice["invoice_number"] == "INV-TEST-999"
        assert invoice["vendor_name"] == "Test Vendor"
        assert invoice["invoice_date"] == "2026-06-10"
        assert Decimal(invoice["total_amount"]) == Decimal("123.45")
        assert invoice["status"] == "uploaded"
        assert invoice["id"] is not None

    async def test_upload_non_pdf_rejected(self, client: AsyncClient, auth_user, tmp_path, monkeypatch):
        import app.services.invoice_service as is_module
        monkeypatch.setattr(is_module, "INVOICES_UPLOAD_DIR", tmp_path / "invoices")

        _, headers = auth_user
        form = _pdf_upload_form(
            filename="document.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            pdf_bytes=b"not a pdf",
        )
        resp = await client.post(
            "/api/v1/invoices/upload",
            headers=headers,
            files=form["files"],
            data=form["data"],
        )
        assert resp.status_code == 400
        assert "PDF" in resp.json()["detail"]

    async def test_upload_txt_extension_rejected(self, client: AsyncClient, auth_user, tmp_path, monkeypatch):
        import app.services.invoice_service as is_module
        monkeypatch.setattr(is_module, "INVOICES_UPLOAD_DIR", tmp_path / "invoices")

        _, headers = auth_user
        form = _pdf_upload_form(
            filename="fake.txt",
            content_type="application/pdf",
            pdf_bytes=b"%PDF content",
        )
        resp = await client.post(
            "/api/v1/invoices/upload",
            headers=headers,
            files=form["files"],
            data=form["data"],
        )
        assert resp.status_code == 400

    async def test_upload_oversized_file_rejected(self, client: AsyncClient, auth_user, tmp_path, monkeypatch):
        import app.services.invoice_service as is_module
        monkeypatch.setattr(is_module, "INVOICES_UPLOAD_DIR", tmp_path / "invoices")
        monkeypatch.setattr(is_module, "MAX_FILE_SIZE", 10)

        _, headers = auth_user
        big_pdf = _make_pdf_bytes(b"X" * 100)
        form = _pdf_upload_form(pdf_bytes=big_pdf, invoice_number="INV-BIG-001")
        resp = await client.post(
            "/api/v1/invoices/upload",
            headers=headers,
            files=form["files"],
            data=form["data"],
        )
        assert resp.status_code == 400
        assert "limit" in resp.json()["detail"].lower()

    async def test_upload_duplicate_invoice_number_rejected(
        self, client: AsyncClient, auth_user, tmp_path, monkeypatch
    ):
        import app.services.invoice_service as is_module
        monkeypatch.setattr(is_module, "INVOICES_UPLOAD_DIR", tmp_path / "invoices")

        _, headers = auth_user
        form = _pdf_upload_form(invoice_number="INV-DUP-001")
        # First upload
        resp1 = await client.post(
            "/api/v1/invoices/upload",
            headers=headers,
            files=form["files"],
            data=form["data"],
        )
        assert resp1.status_code == 201

        # Second upload with same invoice_number
        form2 = _pdf_upload_form(invoice_number="INV-DUP-001")
        resp2 = await client.post(
            "/api/v1/invoices/upload",
            headers=headers,
            files=form2["files"],
            data=form2["data"],
        )
        assert resp2.status_code == 409
        assert "already exists" in resp2.json()["detail"]


# ---------------------------------------------------------------------------
# List Tests
# ---------------------------------------------------------------------------

class TestInvoiceList:
    async def test_list_empty(self, client: AsyncClient, auth_user):
        _, headers = auth_user
        resp = await client.get("/api/v1/invoices/", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "invoices" in body
        assert body["total"] == 0

    async def test_list_returns_uploaded_invoice(
        self, client: AsyncClient, auth_user, uploaded_invoice
    ):
        _, headers = auth_user
        resp = await client.get("/api/v1/invoices/", headers=headers)
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["invoices"]]
        assert uploaded_invoice["id"] in ids

    async def test_list_pagination(self, client: AsyncClient, auth_user):
        _, headers = auth_user
        resp = await client.get(
            "/api/v1/invoices/", headers=headers, params={"page": 1, "page_size": 5}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 1
        assert body["page_size"] == 5

    async def test_list_search_by_vendor_name(self, client: AsyncClient, auth_user, uploaded_invoice):
        _, headers = auth_user
        resp = await client.get(
            "/api/v1/invoices/",
            headers=headers,
            params={"search": "Acme"},
        )
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["invoices"]]
        assert uploaded_invoice["id"] in ids

    async def test_list_search_by_invoice_number(self, client: AsyncClient, auth_user, uploaded_invoice):
        _, headers = auth_user
        resp = await client.get(
            "/api/v1/invoices/",
            headers=headers,
            params={"search": "INV-001"},
        )
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["invoices"]]
        assert uploaded_invoice["id"] in ids


# ---------------------------------------------------------------------------
# Get Invoice Detail Tests
# ---------------------------------------------------------------------------

class TestInvoiceDetail:
    async def test_get_invoice_success(
        self, client: AsyncClient, auth_user, uploaded_invoice
    ):
        _, headers = auth_user
        invoice_id = uploaded_invoice["id"]
        resp = await client.get(f"/api/v1/invoices/{invoice_id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == invoice_id
        assert body["vendor_name"] == uploaded_invoice["vendor_name"]

    async def test_get_invoice_not_found(self, client: AsyncClient, auth_user):
        _, headers = auth_user
        resp = await client.get("/api/v1/invoices/999999", headers=headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Download Tests
# ---------------------------------------------------------------------------

class TestInvoiceDownload:
    async def test_download_success(
        self, client: AsyncClient, auth_user, uploaded_invoice
    ):
        _, headers = auth_user
        invoice_id = uploaded_invoice["id"]
        resp = await client.get(f"/api/v1/invoices/{invoice_id}/download", headers=headers)
        assert resp.status_code == 200
        assert resp.headers["Content-Type"] == "application/pdf"
        assert len(resp.content) > 0

    async def test_download_not_found(self, client: AsyncClient, auth_user):
        _, headers = auth_user
        resp = await client.get("/api/v1/invoices/999999/download", headers=headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete Tests
# ---------------------------------------------------------------------------

class TestInvoiceDelete:
    async def test_delete_success(
        self, client: AsyncClient, auth_user, uploaded_invoice
    ):
        _, headers = auth_user
        invoice_id = uploaded_invoice["id"]
        resp = await client.delete(f"/api/v1/invoices/{invoice_id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["invoice_id"] == invoice_id
        assert "deleted" in body["message"].lower()

        # Confirm it's gone
        get_resp = await client.get(f"/api/v1/invoices/{invoice_id}", headers=headers)
        assert get_resp.status_code == 404

    async def test_delete_not_found(self, client: AsyncClient, auth_user):
        _, headers = auth_user
        resp = await client.delete("/api/v1/invoices/999999", headers=headers)
        assert resp.status_code == 404
