import hashlib
import hmac
import json

from httpx import AsyncClient


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def test_webhook_rejects_bad_signature(client: AsyncClient, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "GITHUB_WEBHOOK_SECRET", "test_webhook_secret")

    body = json.dumps({"action": "opened"}).encode()
    resp = await client.post(
        "/api/v1/github/webhook",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=invalid",
        },
    )
    assert resp.status_code == 401


async def test_webhook_accepts_valid_signature_irrelevant_action(client: AsyncClient, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "GITHUB_WEBHOOK_SECRET", "test_webhook_secret")

    body = json.dumps({"action": "closed"}).encode()
    sig = _sign("test_webhook_secret", body)
    resp = await client.post(
        "/api/v1/github/webhook",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"


async def test_webhook_missing_required_fields(client: AsyncClient, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "GITHUB_WEBHOOK_SECRET", "test_webhook_secret")

    body = json.dumps({"action": "opened"}).encode()  # missing repository/pull_request/installation
    sig = _sign("test_webhook_secret", body)
    resp = await client.post(
        "/api/v1/github/webhook",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == 400


async def test_ensure_system_user_idempotent(db_session):
    from app.api.v1.routes.github import SYSTEM_USER_ID, _ensure_system_user

    user_id_1 = await _ensure_system_user(db_session)
    await db_session.commit()
    user_id_2 = await _ensure_system_user(db_session)

    assert user_id_1 == user_id_2 == SYSTEM_USER_ID


async def test_jwt_creation_for_github_app():
    from cryptography.hazmat.primitives import serialization

    # Use a real-ish RSA key for the test (generate ephemeral)
    from cryptography.hazmat.primitives.asymmetric import rsa

    from app.core.config import settings

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    import app.services.github.github_client as gh_module
    original_key = settings.GITHUB_PRIVATE_KEY
    original_app_id = settings.GITHUB_APP_ID
    settings.GITHUB_PRIVATE_KEY = pem
    settings.GITHUB_APP_ID = "12345"

    try:
        token = gh_module._make_jwt()
        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # header.payload.signature
    finally:
        settings.GITHUB_PRIVATE_KEY = original_key
        settings.GITHUB_APP_ID = original_app_id
