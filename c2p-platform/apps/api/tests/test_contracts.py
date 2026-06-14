"""
Tests for Phase 2: Contract Management Module

Covers:
  - POST /api/v1/contracts/upload
  - GET  /api/v1/contracts/
  - GET  /api/v1/contracts/{id}
  - GET  /api/v1/contracts/{id}/download
  - PATCH /api/v1/contracts/{id}
  - DELETE /api/v1/contracts/{id}

Security tests:
  - Unauthenticated requests return 401

Validation tests:
  - Non-PDF files rejected (400)
  - Files over 20 MB rejected (400)
  - Duplicate contract number rejected (409)
"""
import io
import uuid
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
    vendor_name: str = "Acme Corp",
    contract_number: str = "CTR-001",
    pdf_bytes: bytes | None = None,
    filename: str = "contract.pdf",
    content_type: str = "application/pdf",
):
    """Build the multipart form data for contract upload."""
    if pdf_bytes is None:
        pdf_bytes = _make_pdf_bytes()
    return {
        "files": [("file", (filename, io.BytesIO(pdf_bytes), content_type))],
        "data": {"vendor_name": vendor_name, "contract_number": contract_number},
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def auth_user(db_session) -> tuple[User, dict]:
    """Create a test user with a unique email and return (user, auth_headers)."""
    unique_email = f"contracts-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=unique_email,
        full_name="Contract Tester",
        hashed_password=get_password_hash("securepassword"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    headers = _auth_headers(user.id, user.email)
    return user, headers


@pytest_asyncio.fixture
async def uploaded_contract(client: AsyncClient, auth_user, tmp_path, monkeypatch):
    """
    Upload a single contract and return the JSON response body.
    Patches UPLOAD_DIR to use a temporary directory for isolation.
    """
    import app.services.contract_service as cs_module
    monkeypatch.setattr(cs_module, "UPLOAD_DIR", tmp_path / "contracts")

    _, headers = auth_user
    form = _pdf_upload_form()
    resp = await client.post(
        "/api/v1/contracts/upload",
        headers=headers,
        files=form["files"],
        data=form["data"],
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["contract"]


# ---------------------------------------------------------------------------
# Security Tests
# ---------------------------------------------------------------------------

class TestContractSecurity:
    async def test_upload_requires_auth(self, client: AsyncClient):
        form = _pdf_upload_form()
        resp = await client.post(
            "/api/v1/contracts/upload",
            files=form["files"],
            data=form["data"],
        )
        assert resp.status_code == 401

    async def test_list_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/contracts/")
        assert resp.status_code == 401

    async def test_get_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/contracts/1")
        assert resp.status_code == 401

    async def test_download_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/contracts/1/download")
        assert resp.status_code == 401

    async def test_delete_requires_auth(self, client: AsyncClient):
        resp = await client.delete("/api/v1/contracts/1")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Upload Tests
# ---------------------------------------------------------------------------

class TestContractUpload:
    async def test_upload_success(self, client: AsyncClient, auth_user, tmp_path, monkeypatch):
        import app.services.contract_service as cs_module
        monkeypatch.setattr(cs_module, "UPLOAD_DIR", tmp_path / "contracts")

        _, headers = auth_user
        form = _pdf_upload_form(vendor_name="Test Vendor", contract_number="CTR-TEST-001")
        resp = await client.post(
            "/api/v1/contracts/upload",
            headers=headers,
            files=form["files"],
            data=form["data"],
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["message"] == "Contract uploaded successfully"
        contract = body["contract"]
        assert contract["vendor_name"] == "Test Vendor"
        assert contract["contract_number"] == "CTR-TEST-001"
        assert contract["status"] == "uploaded"
        assert contract["mime_type"] == "application/pdf"
        assert contract["id"] is not None

    async def test_upload_non_pdf_rejected(self, client: AsyncClient, auth_user, tmp_path, monkeypatch):
        import app.services.contract_service as cs_module
        monkeypatch.setattr(cs_module, "UPLOAD_DIR", tmp_path / "contracts")

        _, headers = auth_user
        form = _pdf_upload_form(
            filename="document.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            pdf_bytes=b"not a pdf",
        )
        resp = await client.post(
            "/api/v1/contracts/upload",
            headers=headers,
            files=form["files"],
            data=form["data"],
        )
        assert resp.status_code == 400
        assert "PDF" in resp.json()["detail"]

    async def test_upload_txt_extension_rejected(self, client: AsyncClient, auth_user, tmp_path, monkeypatch):
        import app.services.contract_service as cs_module
        monkeypatch.setattr(cs_module, "UPLOAD_DIR", tmp_path / "contracts")

        _, headers = auth_user
        form = _pdf_upload_form(
            filename="fake.txt",
            content_type="application/pdf",  # correct mime but wrong extension
            pdf_bytes=b"%PDF content",
        )
        resp = await client.post(
            "/api/v1/contracts/upload",
            headers=headers,
            files=form["files"],
            data=form["data"],
        )
        assert resp.status_code == 400

    async def test_upload_oversized_file_rejected(self, client: AsyncClient, auth_user, tmp_path, monkeypatch):
        import app.services.contract_service as cs_module
        upload_dir = tmp_path / "contracts"
        monkeypatch.setattr(cs_module, "UPLOAD_DIR", upload_dir)
        # Override MAX_FILE_SIZE to a tiny limit for testing
        monkeypatch.setattr(cs_module, "MAX_FILE_SIZE", 10)

        _, headers = auth_user
        big_pdf = _make_pdf_bytes(b"X" * 100)  # 100 bytes, > 10 byte limit
        form = _pdf_upload_form(pdf_bytes=big_pdf, contract_number="CTR-BIG-001")
        resp = await client.post(
            "/api/v1/contracts/upload",
            headers=headers,
            files=form["files"],
            data=form["data"],
        )
        assert resp.status_code == 400
        assert "limit" in resp.json()["detail"].lower()

    async def test_upload_duplicate_contract_number_rejected(
        self, client: AsyncClient, auth_user, tmp_path, monkeypatch
    ):
        import app.services.contract_service as cs_module
        monkeypatch.setattr(cs_module, "UPLOAD_DIR", tmp_path / "contracts")

        _, headers = auth_user
        form = _pdf_upload_form(contract_number="CTR-DUP-001")
        # First upload
        resp1 = await client.post(
            "/api/v1/contracts/upload",
            headers=headers,
            files=form["files"],
            data=form["data"],
        )
        assert resp1.status_code == 201

        # Second upload with same contract_number
        form2 = _pdf_upload_form(contract_number="CTR-DUP-001")
        resp2 = await client.post(
            "/api/v1/contracts/upload",
            headers=headers,
            files=form2["files"],
            data=form2["data"],
        )
        assert resp2.status_code == 409
        assert "already exists" in resp2.json()["detail"]

    async def test_upload_stores_correct_metadata(
        self, client: AsyncClient, auth_user, tmp_path, monkeypatch
    ):
        import app.services.contract_service as cs_module
        monkeypatch.setattr(cs_module, "UPLOAD_DIR", tmp_path / "contracts")

        user, headers = auth_user
        form = _pdf_upload_form(vendor_name="Metadata Corp", contract_number="CTR-META-001")
        resp = await client.post(
            "/api/v1/contracts/upload",
            headers=headers,
            files=form["files"],
            data=form["data"],
        )
        contract = resp.json()["contract"]
        assert contract["created_by"] == user.id
        assert contract["file_size"] > 0
        assert contract["upload_date"] is not None


# ---------------------------------------------------------------------------
# List Tests
# ---------------------------------------------------------------------------

class TestContractList:
    async def test_list_empty(self, client: AsyncClient, auth_user):
        _, headers = auth_user
        resp = await client.get("/api/v1/contracts/", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "contracts" in body
        assert "total" in body
        assert "page" in body
        assert "page_size" in body
        assert "total_pages" in body

    async def test_list_returns_uploaded_contract(
        self, client: AsyncClient, auth_user, uploaded_contract
    ):
        _, headers = auth_user
        resp = await client.get("/api/v1/contracts/", headers=headers)
        assert resp.status_code == 200
        ids = [c["id"] for c in resp.json()["contracts"]]
        assert uploaded_contract["id"] in ids

    async def test_list_pagination(self, client: AsyncClient, auth_user):
        _, headers = auth_user
        resp = await client.get(
            "/api/v1/contracts/", headers=headers, params={"page": 1, "page_size": 5}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 1
        assert body["page_size"] == 5

    async def test_list_filter_by_status(self, client: AsyncClient, auth_user, uploaded_contract):
        _, headers = auth_user
        # Filter for "uploaded" status — should find our contract
        resp = await client.get(
            "/api/v1/contracts/", headers=headers, params={"status": "uploaded"}
        )
        assert resp.status_code == 200
        ids = [c["id"] for c in resp.json()["contracts"]]
        assert uploaded_contract["id"] in ids

        # Filter for "processed" — should NOT include freshly uploaded contract
        resp2 = await client.get(
            "/api/v1/contracts/", headers=headers, params={"status": "processed"}
        )
        ids2 = [c["id"] for c in resp2.json()["contracts"]]
        assert uploaded_contract["id"] not in ids2

    async def test_list_search(self, client: AsyncClient, auth_user, uploaded_contract):
        _, headers = auth_user
        # Search by the vendor name used in the fixture
        resp = await client.get(
            "/api/v1/contracts/",
            headers=headers,
            params={"search": "Acme"},
        )
        assert resp.status_code == 200
        # Should find at least our uploaded contract
        ids = [c["id"] for c in resp.json()["contracts"]]
        assert uploaded_contract["id"] in ids

    async def test_list_invalid_page_size(self, client: AsyncClient, auth_user):
        _, headers = auth_user
        resp = await client.get(
            "/api/v1/contracts/", headers=headers, params={"page_size": 200}
        )
        assert resp.status_code == 422  # FastAPI validation error


# ---------------------------------------------------------------------------
# Get Contract Detail Tests
# ---------------------------------------------------------------------------

class TestContractDetail:
    async def test_get_contract_success(
        self, client: AsyncClient, auth_user, uploaded_contract
    ):
        _, headers = auth_user
        contract_id = uploaded_contract["id"]
        resp = await client.get(f"/api/v1/contracts/{contract_id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == contract_id
        assert body["vendor_name"] == uploaded_contract["vendor_name"]

    async def test_get_contract_not_found(self, client: AsyncClient, auth_user):
        _, headers = auth_user
        resp = await client.get("/api/v1/contracts/999999", headers=headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update Tests
# ---------------------------------------------------------------------------

class TestContractUpdate:
    async def test_update_vendor_name(
        self, client: AsyncClient, auth_user, uploaded_contract
    ):
        _, headers = auth_user
        contract_id = uploaded_contract["id"]
        resp = await client.patch(
            f"/api/v1/contracts/{contract_id}",
            headers=headers,
            json={"vendor_name": "Updated Vendor"},
        )
        assert resp.status_code == 200
        assert resp.json()["vendor_name"] == "Updated Vendor"

    async def test_update_status(
        self, client: AsyncClient, auth_user, uploaded_contract
    ):
        _, headers = auth_user
        contract_id = uploaded_contract["id"]
        resp = await client.patch(
            f"/api/v1/contracts/{contract_id}",
            headers=headers,
            json={"status": "processed"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "processed"

    async def test_update_not_found(self, client: AsyncClient, auth_user):
        _, headers = auth_user
        resp = await client.patch(
            "/api/v1/contracts/999999",
            headers=headers,
            json={"vendor_name": "Ghost Vendor"},
        )
        assert resp.status_code == 404

    async def test_update_invalid_status(
        self, client: AsyncClient, auth_user, uploaded_contract
    ):
        _, headers = auth_user
        contract_id = uploaded_contract["id"]
        resp = await client.patch(
            f"/api/v1/contracts/{contract_id}",
            headers=headers,
            json={"status": "invalid_status_value"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Delete Tests
# ---------------------------------------------------------------------------

class TestContractDelete:
    async def test_delete_success(
        self, client: AsyncClient, auth_user, uploaded_contract
    ):
        _, headers = auth_user
        contract_id = uploaded_contract["id"]
        resp = await client.delete(f"/api/v1/contracts/{contract_id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["contract_id"] == contract_id
        assert "deleted" in body["message"].lower()

        # Confirm it's gone
        get_resp = await client.get(f"/api/v1/contracts/{contract_id}", headers=headers)
        assert get_resp.status_code == 404

    async def test_delete_not_found(self, client: AsyncClient, auth_user):
        _, headers = auth_user
        resp = await client.delete("/api/v1/contracts/999999", headers=headers)
        assert resp.status_code == 404
