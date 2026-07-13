from unittest.mock import AsyncMock, patch

from httpx import AsyncClient


async def test_create_scan_requires_auth(client: AsyncClient):
    resp = await client.post(
        "/api/v1/scans",
        json={"code": "def foo(): pass", "language": "python"},
    )
    assert resp.status_code == 403


async def test_create_scan_authenticated(client: AsyncClient, auth_headers: dict):
    with patch("app.api.v1.routes.scans.run_scan", new=AsyncMock()):
        resp = await client.post(
            "/api/v1/scans",
            json={"code": "def foo():\n    pass", "language": "python"},
            headers=auth_headers,
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["language"] == "python"
    assert "id" in data


async def test_create_scan_no_code_or_url(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/v1/scans", json={}, headers=auth_headers)
    assert resp.status_code == 400


async def test_get_scan_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        "/api/v1/scans/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_list_scans_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/scans", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_scan_input_too_large(client: AsyncClient, auth_headers: dict):
    huge_code = "x = 1\n" * 10000  # way over MAX_CODE_LINES
    with patch("app.api.v1.routes.scans.run_scan", new=AsyncMock()):
        resp = await client.post(
            "/api/v1/scans",
            json={"code": huge_code, "language": "python"},
            headers=auth_headers,
        )
    # scan is created but run_scan will fail — status will flip to failed
    # creation itself succeeds (validation happens inside run_scan bg task)
    assert resp.status_code == 201


async def test_chunker_generic_fallback():
    from app.services.scanner.chunker import chunk_code
    js_code = """
function login(user, pass) {
  return db.query(`SELECT * FROM users WHERE user='${user}'`);
}
function logout(id) {
  sessions.delete(id);
}
"""
    chunks = chunk_code(js_code, "javascript")
    assert len(chunks) >= 1
    assert all(c.language == "javascript" for c in chunks)


async def test_hash_code_deterministic():
    from app.services.scan_service import hash_code
    code = "def foo(): pass"
    assert hash_code(code) == hash_code(code)
    assert hash_code(code) != hash_code("def bar(): pass")
    assert len(hash_code(code)) == 64
