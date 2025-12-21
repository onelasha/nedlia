"""Pytest fixtures for consistency tests."""

import os

import httpx
import pytest


@pytest.fixture
def base_url():
    return os.getenv("BASE_URL", "http://localhost:8000")


@pytest.fixture
async def api_client(base_url):
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        yield client


@pytest.fixture
def slo_seconds():
    """Consistency SLO in seconds."""
    return float(os.getenv("CONSISTENCY_SLO_SECONDS", "5.0"))
