import sys
from pathlib import Path

import mongomock
import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import get_db  # noqa: E402
from main import app  # noqa: E402


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class FakeAsyncClient:
    """Drop-in replacement for httpx.AsyncClient used by app.auth.

    Stores the constructor kwargs for assertions and returns a configured
    response (or raises a configured exception) from .get().
    """

    next_response: FakeResponse | None = None
    next_exception: Exception | None = None
    last_url: str | None = None
    last_headers: dict | None = None

    def __init__(self, *_, **__):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def get(self, url, headers=None):
        FakeAsyncClient.last_url = url
        FakeAsyncClient.last_headers = headers
        if FakeAsyncClient.next_exception is not None:
            raise FakeAsyncClient.next_exception
        assert FakeAsyncClient.next_response is not None, "configure FakeAsyncClient.next_response"
        return FakeAsyncClient.next_response


@pytest.fixture
def fake_google(monkeypatch):
    """Replaces httpx.AsyncClient inside app.auth and resets per-test state."""
    import app.auth as auth_module

    FakeAsyncClient.next_response = None
    FakeAsyncClient.next_exception = None
    FakeAsyncClient.last_url = None
    FakeAsyncClient.last_headers = None
    monkeypatch.setattr(auth_module.httpx, "AsyncClient", FakeAsyncClient)

    def set_user(payload: dict, status_code: int = 200) -> None:
        FakeAsyncClient.next_response = FakeResponse(status_code, payload)

    def set_error(exc: Exception) -> None:
        FakeAsyncClient.next_exception = exc

    return type(
        "FakeGoogle", (), {"set_user": staticmethod(set_user), "set_error": staticmethod(set_error)}
    )


@pytest.fixture
def mock_db():
    return mongomock.MongoClient()["test_db"]


@pytest.fixture
def client(mock_db):
    async_client = AsyncMongoMockClient(mock_mongo_client=mock_db.client)
    async_db = async_client["test_db"]
    app.dependency_overrides[get_db] = lambda: async_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def google_payload(**overrides) -> dict:
    """Realistic userinfo payload — Google sends all these with `openid email profile`."""
    base = {
        "sub": "1234567890",
        "email": "alice@example.com",
        "email_verified": True,
        "name": "Alice Example",
        "given_name": "Alice",
        "family_name": "Example",
        "picture": "https://lh3.googleusercontent.com/a/avatar.jpg",
        "locale": "cs",
        "hd": "example.com",
    }
    base.update(overrides)
    return base
