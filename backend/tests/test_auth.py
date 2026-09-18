import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    res = await client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "safety_note" in data


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    res = await client.post("/api/v1/auth/login", json={"email": "wrong@test.com", "password": "wrong"})
    assert res.status_code == 401
    data = res.json()
    err = data.get("detail", {}).get("error", {}) or data.get("error", {})
    assert err.get("code") == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_register_clinician(client):
    res = await client.post("/api/v1/auth/register", json={
        "email": "newclinician@test.com",
        "password": "Password123!",
        "display_name": "Dr. Smith",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "newclinician@test.com"
    assert data["role"] == "clinician"
