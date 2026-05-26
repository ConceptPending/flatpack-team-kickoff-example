"""Explicit coverage of the CSRF middleware contract.

Re-pointed from /api/admin/items (deleted with the Item slice) to
/api/admin/checklist-templates — same contract, just a different
endpoint to target.
"""

import pytest

from tests.conftest import TEST_ADMIN_EMAIL

_MINIMAL_TEMPLATE = {"name": "csrf-test", "sections": []}


async def _login(client) -> str:
    resp = await client.post(
        "/api/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": "testpass"},
    )
    assert resp.status_code == 200
    return resp.cookies["csrf_token"]


@pytest.mark.asyncio
async def test_write_without_csrf_header_is_forbidden(client):
    """After login the csrf cookie is present, but a POST without the
    matching X-CSRF-Token header is the classic CSRF attack shape — 403."""
    await _login(client)
    response = await client.post(
        "/api/admin/checklist-templates",
        json=_MINIMAL_TEMPLATE,
    )
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]


@pytest.mark.asyncio
async def test_write_with_mismatched_csrf_token_is_forbidden(client):
    await _login(client)
    response = await client.post(
        "/api/admin/checklist-templates",
        json=_MINIMAL_TEMPLATE,
        headers={"X-CSRF-Token": "not-the-real-token"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_write_with_matching_csrf_token_succeeds(client):
    csrf = await _login(client)
    response = await client.post(
        "/api/admin/checklist-templates",
        json=_MINIMAL_TEMPLATE,
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_safe_methods_dont_require_csrf(client):
    """GET / HEAD / OPTIONS are always allowed regardless of csrf state."""
    await _login(client)
    response = await client.get("/api/admin/checklist-templates")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_login_is_exempt(client):
    """Login can't have a prior csrf token; it issues one."""
    response = await client.post(
        "/api/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": "testpass"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_csrf_endpoint_returns_token_and_sets_cookie(client):
    response = await client.get("/api/auth/csrf")
    assert response.status_code == 200
    body = response.json()
    assert "token" in body
    assert len(body["token"]) >= 32
    assert response.cookies["csrf_token"] == body["token"]


@pytest.mark.asyncio
async def test_anonymous_write_is_forbidden(client):
    """No login, no cookie, no header — middleware 403s before auth even runs."""
    response = await client.post(
        "/api/admin/checklist-templates",
        json=_MINIMAL_TEMPLATE,
    )
    assert response.status_code == 403
