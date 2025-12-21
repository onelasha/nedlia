"""Pytest fixtures for chaos tests."""

import os

import boto3
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
def sqs_client():
    return boto3.client(
        "sqs",
        endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )


@pytest.fixture
def cloudwatch_client():
    return boto3.client(
        "cloudwatch",
        endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )
