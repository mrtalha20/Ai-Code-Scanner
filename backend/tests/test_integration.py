"""
Integration test: posts a known-vulnerable Python snippet and asserts
at least one finding is returned with OWASP A03 (Injection).
Requires a running backend at SCANNER_API_URL and a valid API key.
"""
import os
import time

import httpx
import pytest

BASE = os.getenv("SCANNER_API_URL", "http://localhost:8000")
TEST_EMAIL = "integration_test@scanner.test"
TEST_PASS = "Integration_Test_Pass_123"

VULNERABLE_CODE = """
import sqlite3

def get_user(user_id):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchone()

def store_secret(key, value):
    import hashlib
    hashed = hashlib.md5(value.encode()).hexdigest()
    return hashed
"""


@pytest.fixture(scope="module")
def auth_token():
    with httpx.Client(base_url=BASE, timeout=30) as client:
        # Register (ignore if already exists)
        client.post("/api/v1/auth/register", json={"email": TEST_EMAIL, "password": TEST_PASS})
        resp = client.post("/api/v1/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASS})
        resp.raise_for_status()
        return resp.json()["access_token"]


def test_health():
    resp = httpx.get(f"{BASE}/health", timeout=10)
    assert resp.status_code == 200
    assert resp.json()["status"] in ("ok", "degraded")


def test_full_scan_pipeline(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}

    with httpx.Client(base_url=BASE, timeout=60) as client:
        # Create scan
        resp = client.post(
            "/api/v1/scans",
            json={"code": VULNERABLE_CODE, "language": "python"},
            headers=headers,
        )
        assert resp.status_code == 201, f"Scan creation failed: {resp.text}"
        scan_id = resp.json()["id"]

        # Poll until done (max 3 minutes)
        for _ in range(36):
            time.sleep(5)
            poll = client.get(f"/api/v1/scans/{scan_id}", headers=headers)
            assert poll.status_code == 200
            data = poll.json()
            if data["status"] == "done":
                break
            if data["status"] == "failed":
                pytest.fail(f"Scan failed: {data.get('error_message')}")
        else:
            pytest.fail("Scan timed out after 3 minutes")

        # Validate findings
        findings = data["findings"]
        assert len(findings) >= 1, "Expected at least one finding for SQL injection"

        categories = [f["owasp_category"] for f in findings]
        assert any("A03" in c or "Injection" in c for c in categories), (
            f"Expected SQL injection finding. Got: {categories}"
        )

        # All findings should have required fields
        for f in findings:
            assert 1 <= f["severity"] <= 10
            assert f["vulnerable_code"]
            assert f["fixed_code"]
            assert f["description"]
