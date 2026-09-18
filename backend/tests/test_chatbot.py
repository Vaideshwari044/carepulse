import pytest
from app.services.chatbot import (
    deidentify_text,
    check_emergency_symptoms,
    MANDATORY_DISCLAIMER,
)


def test_deidentify_text():
    text = "John Doe (john.doe@example.com, phone 555-123-4567, patient P101) wants advice."
    scrubbed = deidentify_text(text)
    assert "john.doe@example.com" not in scrubbed
    assert "555-123-4567" not in scrubbed
    assert "P101" not in scrubbed
    assert "[REDACTED_EMAIL]" in scrubbed
    assert "[REDACTED_PHONE]" in scrubbed
    assert "[REDACTED_MRN]" in scrubbed


def test_check_emergency_symptoms():
    chest_pain = "I have crushing chest pain and tightness."
    res = check_emergency_symptoms(chest_pain)
    assert res is not None
    assert "IMMEDIATE EMERGENCY MEDICAL CARE REQUIRED" in res

    normal_msg = "How much water should I drink daily?"
    res_normal = check_emergency_symptoms(normal_msg)
    assert res_normal is None


@pytest.mark.asyncio
async def test_chat_endpoint_unauthenticated(client):
    response = await client.post("/api/v1/chat", json={"message": "How to sleep better?"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_endpoint_authenticated(client, async_db):
    # First login as admin
    login_res = await client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "AdminPass123!"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    chat_res = await client.post(
        "/api/v1/chat",
        json={"message": "What is a healthy lifestyle?"},
        headers=headers,
    )
    assert chat_res.status_code == 200
    data = chat_res.json()
    assert "response" in data
    assert "timestamp" in data
    assert "conversation_id" in data
    assert data["emergency_warning"] is False
    assert MANDATORY_DISCLAIMER in data["response"]


@pytest.mark.asyncio
async def test_chat_endpoint_emergency_warning(client, async_db):
    login_res = await client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "AdminPass123!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    chat_res = await client.post(
        "/api/v1/chat",
        json={"message": "I have sudden crushing chest pain and can't breathe!"},
        headers=headers,
    )
    assert chat_res.status_code == 200
    data = chat_res.json()
    assert data["emergency_warning"] is True
    assert "EMERGENCY" in data["response"]
