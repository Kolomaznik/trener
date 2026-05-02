import asyncio

import httpx
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth import GoogleUser, get_current_user
from tests.conftest import google_payload


def test_google_user_accepts_full_payload():
    user = GoogleUser.model_validate(google_payload())
    assert user.email == "alice@example.com"
    assert user.sub == "1234567890"
    assert user.name == "Alice Example"
    assert str(user.picture).startswith("https://")
    assert user.locale == "cs"
    assert user.email_verified is True


def test_google_user_accepts_unknown_extra_fields():
    """Future-proofing: if Google adds new fields, validation must not fail."""
    payload = google_payload(future_field="surprise", another={"nested": 1})
    user = GoogleUser.model_validate(payload)
    dumped = user.model_dump(mode="json")
    assert dumped["future_field"] == "surprise"
    assert dumped["another"] == {"nested": 1}


def test_get_current_user_valid_token(fake_google):
    fake_google.set_user(google_payload())
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="tok")
    user = asyncio.run(get_current_user(creds))
    assert user.email == "alice@example.com"


def test_get_current_user_passes_bearer_header_to_google(fake_google):
    from tests.conftest import FakeAsyncClient

    fake_google.set_user(google_payload())
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="abc123")
    asyncio.run(get_current_user(creds))
    assert FakeAsyncClient.last_headers == {"Authorization": "Bearer abc123"}


def test_get_current_user_invalid_token_returns_401(fake_google):
    fake_google.set_user({"error": "invalid_token"}, status_code=401)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_current_user(creds))
    assert exc.value.status_code == 401


def test_get_current_user_network_error_returns_502(fake_google):
    fake_google.set_error(httpx.ConnectError("dns failed"))
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="tok")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_current_user(creds))
    assert exc.value.status_code == 502
