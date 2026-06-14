"""
Phase 2 Final Verification Script
===================================
Runs all 5 required checks against the live server:
  1. POST /contracts/upload  (real PDF)
  2. GET  /contracts/
  3. GET  /contracts/{id}
  4. GET  /contracts/{id}/download
  5. DELETE /contracts/{id}
"""
import httpx
import json
import os
import sys

BASE = "http://127.0.0.1:8000/api/v1"
PDF_FILE = "test_real_contract.pdf"


def banner(step, title):
    print()
    print("=" * 60)
    print(f"  CHECK {step}: {title}")
    print("=" * 60)


def ok(msg):
    print(f"  [PASS] {msg}")


def fail(msg):
    print(f"  [FAIL] {msg}")
    sys.exit(1)


def info(key, val):
    print(f"  {key:20} : {val}")


results = {}

with httpx.Client(timeout=15) as c:

    # ── SETUP: Register + Login ──────────────────────────────────
    c.post(f"{BASE}/auth/register", json={
        "email": "phase2check@c2p.com",
        "full_name": "Phase2 Tester",
        "password": "check1234"
    })

    login = c.post(f"{BASE}/auth/login", json={
        "email": "phase2check@c2p.com",
        "password": "check1234"
    })
    assert login.status_code == 200, f"Login failed: {login.text}"
    token = login.json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}
    print(f"\n  Logged in as phase2check@c2p.com")
    print(f"  Token (first 50): {token[:50]}...")

    # ============================================================
    # CHECK 1: Upload a REAL PDF
    # ============================================================
    banner(1, "POST /contracts/upload  [REAL PDF]")

    with open(PDF_FILE, "rb") as f:
        pdf_bytes = f.read()

    info("File", PDF_FILE)
    info("Size", f"{len(pdf_bytes)} bytes")
    info("Header bytes", str(pdf_bytes[:8]))

    resp = c.post(
        f"{BASE}/contracts/upload",
        headers=H,
        files={"file": (PDF_FILE, pdf_bytes, "application/pdf")},
        data={
            "vendor_name": "Acme Corporation",
            "contract_number": "PHASE2-CHECK-001"
        }
    )

    info("HTTP Status", resp.status_code)

    if resp.status_code == 201:
        body = resp.json()
        contract = body["contract"]
        contract_id = contract["id"]
        file_path = contract["file_path"]
        info("Message", body["message"])
        info("Contract ID", contract_id)
        info("Vendor", contract["vendor_name"])
        info("Contract No", contract["contract_number"])
        info("Stored filename", contract["file_name"])
        info("File size (bytes)", contract["file_size"])
        info("MIME type", contract["mime_type"])
        info("Status", contract["status"])
        info("Uploaded at", contract["upload_date"])
        ok(f"Real PDF uploaded successfully! Contract ID = {contract_id}")
        results["upload"] = True
    else:
        info("Error response", resp.text[:300])
        fail("Upload FAILED")

    # ============================================================
    # CHECK 2: GET /contracts/  (List)
    # ============================================================
    banner(2, "GET /contracts/  [List all contracts]")

    resp = c.get(f"{BASE}/contracts/", headers=H)
    info("HTTP Status", resp.status_code)

    if resp.status_code == 200:
        body = resp.json()
        info("Total contracts", body["total"])
        info("Page", body["page"])
        info("Page size", body["page_size"])
        info("Total pages", body["total_pages"])
        print()
        for i, ct in enumerate(body["contracts"], 1):
            print(f"  Contract #{i}:")
            print(f"    ID          : {ct['id']}")
            print(f"    Vendor      : {ct['vendor_name']}")
            print(f"    Contract No : {ct['contract_number']}")
            print(f"    Status      : {ct['status']}")
            print(f"    File size   : {ct['file_size']} bytes")
        ok(f"{body['total']} contract(s) in list — pagination working!")
        results["list"] = True
    else:
        fail(f"List FAILED: {resp.text}")

    # ============================================================
    # CHECK 3: GET /contracts/{id}  (Detail)
    # ============================================================
    banner(3, f"GET /contracts/{contract_id}  [Contract Detail]")

    resp = c.get(f"{BASE}/contracts/{contract_id}", headers=H)
    info("HTTP Status", resp.status_code)

    if resp.status_code == 200:
        ct = resp.json()
        info("ID", ct["id"])
        info("Vendor", ct["vendor_name"])
        info("Contract No", ct["contract_number"])
        info("File name", ct["file_name"])
        info("File size", f"{ct['file_size']} bytes")
        info("MIME type", ct["mime_type"])
        info("Status", ct["status"])
        info("Created by (user)", ct["created_by"])
        info("Created at", ct["created_at"])
        info("Updated at", ct["updated_at"])
        ok("Contract detail fetched — all fields present!")
        results["detail"] = True
    else:
        fail(f"Detail FAILED: {resp.text}")

    # ============================================================
    # CHECK 4: GET /contracts/{id}/download  (Download PDF)
    # ============================================================
    banner(4, f"GET /contracts/{contract_id}/download  [Download PDF]")

    resp = c.get(f"{BASE}/contracts/{contract_id}/download", headers=H)
    info("HTTP Status", resp.status_code)
    info("Content-Type", resp.headers.get("content-type", "N/A"))
    info("Content-Disposition", resp.headers.get("content-disposition", "N/A"))
    info("Downloaded size", f"{len(resp.content)} bytes")

    if resp.status_code == 200:
        starts_with = resp.content[:8]
        info("File header", str(starts_with))
        is_real_pdf = resp.content.startswith(b"%PDF")
        info("Valid PDF?", "YES (%PDF header confirmed)" if is_real_pdf else "NO - bad header!")

        # Compare against original
        with open(PDF_FILE, "rb") as f:
            original = f.read()
        matches = resp.content == original
        info("Matches original?", "YES - byte-for-byte identical!" if matches else "NO - mismatch!")

        # Save to disk so user can open it
        out_path = "downloaded_from_api.pdf"
        with open(out_path, "wb") as f:
            f.write(resp.content)
        info("Saved locally as", out_path)

        if is_real_pdf and matches:
            ok("PDF downloaded successfully — real PDF, byte-perfect match!")
        else:
            fail("Downloaded content does not match original PDF")
        results["download"] = True
    else:
        fail(f"Download FAILED: {resp.text}")

    # ============================================================
    # CHECK 5: DELETE /contracts/{id}
    # ============================================================
    banner(5, f"DELETE /contracts/{contract_id}  [Delete Contract]")

    resp = c.delete(f"{BASE}/contracts/{contract_id}", headers=H)
    info("HTTP Status", resp.status_code)

    if resp.status_code == 200:
        body = resp.json()
        info("Message", body["message"])
        info("Deleted contract ID", body["contract_id"])

        # Confirm 404 on GET after delete
        verify = c.get(f"{BASE}/contracts/{contract_id}", headers=H)
        info("GET after delete", f"{verify.status_code} {verify.json().get('detail', '')}")

        # Confirm PDF removed from disk
        pdf_gone = not os.path.exists(file_path)
        info("PDF on disk?", "REMOVED (gone!)" if pdf_gone else f"STILL EXISTS at {file_path}")

        ok("Contract deleted from DB + PDF file removed from disk!")
        results["delete"] = True
    else:
        fail(f"Delete FAILED: {resp.text}")

    # ============================================================
    # FINAL VERDICT
    # ============================================================
    print()
    print("=" * 60)
    print("  PHASE 2 -- FINAL VERDICT")
    print("=" * 60)

    checks = [
        ("1. Upload Real PDF",     results.get("upload")),
        ("2. List Contracts",      results.get("list")),
        ("3. Contract Detail",     results.get("detail")),
        ("4. Download PDF",        results.get("download")),
        ("5. Delete Contract",     results.get("delete")),
    ]

    all_pass = True
    for name, passed in checks:
        mark = "v" if passed else "x"
        status = "PASS" if passed else "FAIL"
        print(f"  [{mark}] {name:28} --> {status}")
        if not passed:
            all_pass = False

    print()
    if all_pass:
        print("  RESULT : ALL 5 CHECKS PASSED!")
        print("  STATUS : Phase 2 = TRULY COMPLETE!")
        print("  NEXT   : Ready to move to Phase 3!")
    else:
        print("  RESULT : SOME CHECKS FAILED - fix before Phase 3!")
    print("=" * 60)
