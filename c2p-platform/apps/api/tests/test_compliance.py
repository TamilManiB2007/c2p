"""
Tests for Phase 4: Compliance Foundation

Covers:
  - POST /api/v1/compliance/run
  - GET  /api/v1/compliance/checks/{id}
  - GET  /api/v1/compliance/violations
  - GET  /api/v1/compliance/violations/{id}

Rule Engine tests:
  - Vendor mismatch
  - Contract expired
  - Invoice amount exceeds contract amount
  - Combined scenarios and nullable fields
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
    return b"%PDF-1.4\n" + content


def _auth_headers(user_id: int, email: str) -> dict:
    token = create_access_token(data={"user_id": user_id, "email": email})
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def auth_user(db_session) -> tuple[User, dict]:
    """Create a test user and return (user, auth_headers)."""
    unique_email = f"compliance-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=unique_email,
        full_name="Compliance Tester",
        hashed_password=get_password_hash("securepassword"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    headers = _auth_headers(user.id, user.email)
    return user, headers


@pytest_asyncio.fixture
async def helper_upload(client: AsyncClient, auth_user, tmp_path, monkeypatch):
    """
    Returns helper functions to upload contracts and invoices with temporary folder patching.
    """
    import app.services.contract_service as cs_module
    import app.services.invoice_service as is_module

    monkeypatch.setattr(cs_module, "UPLOAD_DIR", tmp_path / "contracts")
    monkeypatch.setattr(is_module, "INVOICES_UPLOAD_DIR", tmp_path / "invoices")

    _, headers = auth_user

    async def _upload_contract(
        vendor_name: str = "Acme Corp",
        contract_number: str = None,
        end_date: str = None,
        contract_amount: str = None,
    ):
        if not contract_number:
            contract_number = f"CTR-{uuid.uuid4().hex[:6].upper()}"
        data = {
            "vendor_name": vendor_name,
            "contract_number": contract_number,
        }
        if end_date:
            data["end_date"] = end_date
        if contract_amount:
            data["contract_amount"] = contract_amount

        files = [("file", ("contract.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf"))]
        resp = await client.post("/api/v1/contracts/upload", headers=headers, files=files, data=data)
        assert resp.status_code == 201, resp.text
        return resp.json()["contract"]

    async def _upload_invoice(
        invoice_number: str = None,
        vendor_name: str = "Acme Corp",
        invoice_date: str = "2026-06-10",
        total_amount: str = "100.00",
    ):
        if not invoice_number:
            invoice_number = f"INV-{uuid.uuid4().hex[:6].upper()}"
        data = {
            "invoice_number": invoice_number,
            "vendor_name": vendor_name,
            "invoice_date": invoice_date,
            "total_amount": total_amount,
        }
        files = [("file", ("invoice.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf"))]
        resp = await client.post("/api/v1/invoices/upload", headers=headers, files=files, data=data)
        assert resp.status_code == 201, resp.text
        return resp.json()["invoice"]

    return _upload_contract, _upload_invoice


# ---------------------------------------------------------------------------
# Security Tests
# ---------------------------------------------------------------------------

class TestComplianceSecurity:
    async def test_run_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/compliance/run", json={"contract_id": 1, "invoice_id": 1})
        assert resp.status_code == 401

    async def test_get_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/compliance/checks/1")
        assert resp.status_code == 401

    async def test_list_violations_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/compliance/violations")
        assert resp.status_code == 401

    async def test_get_violation_detail_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/compliance/violations/1")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Rule Engine Tests
# ---------------------------------------------------------------------------

class TestComplianceRules:
    async def test_rule_vendor_mismatch(self, client: AsyncClient, auth_user, helper_upload):
        _upload_contract, _upload_invoice = helper_upload
        _, headers = auth_user

        # Contract with "Acme Corp", Invoice with "Beta Inc"
        contract = await _upload_contract(vendor_name="Acme Corp")
        invoice = await _upload_invoice(vendor_name="Beta Inc")

        resp = await client.post(
            "/api/v1/compliance/run",
            headers=headers,
            json={"contract_id": contract["id"], "invoice_id": invoice["id"]},
        )
        assert resp.status_code == 201
        check = resp.json()
        assert check["status"] == "failed"
        assert check["details"]["vendor_mismatch"]["status"] == "failed"
        assert "mismatch" in check["details"]["vendor_mismatch"]["detail"].lower()

    async def test_rule_contract_expired(self, client: AsyncClient, auth_user, helper_upload):
        _upload_contract, _upload_invoice = helper_upload
        _, headers = auth_user

        # Contract ends on 2026-01-01, Invoice is dated 2026-01-02 (Expired)
        contract = await _upload_contract(end_date="2026-01-01")
        invoice = await _upload_invoice(invoice_date="2026-01-02")

        resp = await client.post(
            "/api/v1/compliance/run",
            headers=headers,
            json={"contract_id": contract["id"], "invoice_id": invoice["id"]},
        )
        assert resp.status_code == 201
        check = resp.json()
        assert check["status"] == "failed"
        assert check["details"]["contract_expired"]["status"] == "failed"
        assert "after" in check["details"]["contract_expired"]["detail"].lower()

    async def test_rule_invoice_amount_exceeded(self, client: AsyncClient, auth_user, helper_upload):
        _upload_contract, _upload_invoice = helper_upload
        _, headers = auth_user

        # Contract limit 5000.00, Invoice amount 5000.01 (Exceeded)
        contract = await _upload_contract(contract_amount="5000.00")
        invoice = await _upload_invoice(total_amount="5000.01")

        resp = await client.post(
            "/api/v1/compliance/run",
            headers=headers,
            json={"contract_id": contract["id"], "invoice_id": invoice["id"]},
        )
        assert resp.status_code == 201
        check = resp.json()
        assert check["status"] == "failed"
        assert check["details"]["amount_exceeded"]["status"] == "failed"
        assert "exceeds" in check["details"]["amount_exceeded"]["detail"].lower()

    async def test_rule_fully_compliant(self, client: AsyncClient, auth_user, helper_upload):
        _upload_contract, _upload_invoice = helper_upload
        _, headers = auth_user

        # Contract: Acme Corp, ends 2026-12-31, limit 10000.00
        # Invoice: Acme Corp, dated 2026-06-10, amount 9500.00 (Compliant)
        contract = await _upload_contract(vendor_name="Acme Corp", end_date="2026-12-31", contract_amount="10000.00")
        invoice = await _upload_invoice(vendor_name="Acme Corp", invoice_date="2026-06-10", total_amount="9500.00")

        resp = await client.post(
            "/api/v1/compliance/run",
            headers=headers,
            json={"contract_id": contract["id"], "invoice_id": invoice["id"]},
        )
        assert resp.status_code == 201
        check = resp.json()
        assert check["status"] == "passed"
        assert check["details"]["vendor_mismatch"]["status"] == "passed"
        assert check["details"]["contract_expired"]["status"] == "passed"
        assert check["details"]["amount_exceeded"]["status"] == "passed"

    async def test_rule_case_insensitivity_and_nullable(self, client: AsyncClient, auth_user, helper_upload):
        _upload_contract, _upload_invoice = helper_upload
        _, headers = auth_user

        # Case-insensitivity: "  ACME CORP  " vs "acme corp" should pass
        # Nullable limits: No expiration date, no contract limit should pass
        contract = await _upload_contract(vendor_name="  ACME CORP  ")
        invoice = await _upload_invoice(vendor_name="acme corp")

        resp = await client.post(
            "/api/v1/compliance/run",
            headers=headers,
            json={"contract_id": contract["id"], "invoice_id": invoice["id"]},
        )
        assert resp.status_code == 201
        check = resp.json()
        assert check["status"] == "passed"
        assert check["details"]["vendor_mismatch"]["status"] == "passed"
        assert check["details"]["contract_expired"]["status"] == "passed"
        assert check["details"]["amount_exceeded"]["status"] == "passed"


# ---------------------------------------------------------------------------
# API Query & Violation Tests
# ---------------------------------------------------------------------------

class TestComplianceQuery:
    async def test_get_check_details_success(self, client: AsyncClient, auth_user, helper_upload):
        _upload_contract, _upload_invoice = helper_upload
        _, headers = auth_user

        contract = await _upload_contract()
        invoice = await _upload_invoice()

        # Run
        run_resp = await client.post(
            "/api/v1/compliance/run",
            headers=headers,
            json={"contract_id": contract["id"], "invoice_id": invoice["id"]},
        )
        check_id = run_resp.json()["id"]

        # Retrieve
        get_resp = await client.get(f"/api/v1/compliance/checks/{check_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == check_id

    async def test_get_check_details_not_found(self, client: AsyncClient, auth_user):
        _, headers = auth_user
        resp = await client.get("/api/v1/compliance/checks/99999", headers=headers)
        assert resp.status_code == 404

    async def test_list_violations_only(self, client: AsyncClient, auth_user, helper_upload):
        _upload_contract, _upload_invoice = helper_upload
        _, headers = auth_user

        # 1. Create a passing check
        c1 = await _upload_contract(vendor_name="Acme Corp")
        i1 = await _upload_invoice(vendor_name="Acme Corp")
        await client.post(
            "/api/v1/compliance/run",
            headers=headers,
            json={"contract_id": c1["id"], "invoice_id": i1["id"]},
        )

        # 2. Create a failing check (violation)
        c2 = await _upload_contract(vendor_name="Beta Inc")
        i2 = await _upload_invoice(vendor_name="Acme Corp")
        fail_resp = await client.post(
            "/api/v1/compliance/run",
            headers=headers,
            json={"contract_id": c2["id"], "invoice_id": i2["id"]},
        )
        fail_id = fail_resp.json()["id"]

        # List violations
        violation_resp = await client.get("/api/v1/compliance/violations", headers=headers)
        assert violation_resp.status_code == 200
        violation_list = violation_resp.json()
        assert len(violation_list) == 1
        assert violation_list[0]["id"] == fail_id
        assert violation_list[0]["status"] == "failed"

    async def test_get_violation_details_failed_vs_passed(self, client: AsyncClient, auth_user, helper_upload):
        _upload_contract, _upload_invoice = helper_upload
        _, headers = auth_user

        # 1. Passed check
        c1 = await _upload_contract(vendor_name="Acme Corp")
        i1 = await _upload_invoice(vendor_name="Acme Corp")
        pass_resp = await client.post(
            "/api/v1/compliance/run",
            headers=headers,
            json={"contract_id": c1["id"], "invoice_id": i1["id"]},
        )
        pass_id = pass_resp.json()["id"]

        # 2. Failed check
        c2 = await _upload_contract(vendor_name="Beta Inc")
        i2 = await _upload_invoice(vendor_name="Acme Corp")
        fail_resp = await client.post(
            "/api/v1/compliance/run",
            headers=headers,
            json={"contract_id": c2["id"], "invoice_id": i2["id"]},
        )
        fail_id = fail_resp.json()["id"]

        # GET violation detail of failed check -> should succeed (200)
        resp1 = await client.get(f"/api/v1/compliance/violations/{fail_id}", headers=headers)
        assert resp1.status_code == 200
        assert resp1.json()["id"] == fail_id

        # GET violation detail of passed check -> should fail (404)
        resp2 = await client.get(f"/api/v1/compliance/violations/{pass_id}", headers=headers)
        assert resp2.status_code == 404
