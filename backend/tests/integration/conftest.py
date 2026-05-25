"""Fixtures for integration pipeline tests."""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.security import DEV_USER_ID, get_admin_user, get_current_user
from app.main import app


class FakeRedis:
    """In-memory Redis stand-in for queue integration tests."""

    def __init__(self) -> None:
        self.lists: dict[str, list[str]] = {}
        self.hashes: dict[str, dict[str, str]] = {}

    async def rpush(self, key: str, value: str) -> int:
        self.lists.setdefault(key, []).append(value)
        return len(self.lists[key])

    async def lpop(self, key: str) -> str | None:
        items = self.lists.get(key, [])
        if not items:
            return None
        return items.pop(0)

    async def hset(self, key: str, field: str, value: str) -> int:
        self.hashes.setdefault(key, {})[field] = value
        return 1

    async def hdel(self, key: str, field: str) -> int:
        removed = self.hashes.get(key, {}).pop(field, None)
        return 1 if removed is not None else 0

    async def hget(self, key: str, field: str) -> str | None:
        return self.hashes.get(key, {}).get(field)

    async def hlen(self, key: str) -> int:
        return len(self.hashes.get(key, {}))

    async def llen(self, key: str) -> int:
        return len(self.lists.get(key, []))


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def patch_redis(monkeypatch, fake_redis: FakeRedis):
    monkeypatch.setattr("app.services.job_queue.get_redis", lambda: fake_redis)
    return fake_redis


@pytest.fixture
def admin_client() -> TestClient:
    admin_user = {
        "id": DEV_USER_ID,
        "email": "admin@docmind.local",
        "role": "authenticated",
        "org_id": None,
        "app_metadata": {"role": "admin"},
        "user_metadata": {},
    }

    async def _override_user() -> dict[str, Any]:
        return admin_user

    async def _override_admin() -> dict[str, Any]:
        return admin_user

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_admin_user] = _override_admin
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
