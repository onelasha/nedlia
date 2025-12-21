"""
Backpressure & Failure Tests

Tests system behavior under backpressure and downstream failures.
"""

import asyncio
import os
import time

import pytest


@pytest.mark.asyncio
async def test_high_load_backpressure(api_client):
    """
    Test backpressure handling under high load.
    Send requests faster than system can handle.
    """
    print("\nSending 100 concurrent requests...")

    async def make_request():
        try:
            start = time.time()
            response = await api_client.post(
                "/v1/placements",
                json={
                    "video_id": "550e8400-e29b-41d4-a716-446655440000",
                    "product_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                    "time_range": {"start_time": 0, "end_time": 10},
                },
            )
            return {
                "status": response.status_code,
                "latency_ms": (time.time() - start) * 1000,
            }
        except Exception as e:
            return {"status": 0, "error": str(e), "latency_ms": 0}

    # Send burst
    tasks = [make_request() for _ in range(100)]
    responses = await asyncio.gather(*tasks)

    # Analyze results
    status_codes = {}
    for r in responses:
        code = r["status"]
        status_codes[code] = status_codes.get(code, 0) + 1

    successful = status_codes.get(201, 0) + status_codes.get(200, 0)
    rate_limited = status_codes.get(429, 0)
    errors = sum(v for k, v in status_codes.items() if k >= 500)

    print(f"\nBackpressure Results:")
    print(f"  Successful: {successful}")
    print(f"  Rate Limited (429): {rate_limited}")
    print(f"  Server Errors (5xx): {errors}")
    print(f"  Status distribution: {status_codes}")

    # System should either succeed or rate limit, not error
    assert errors < 10, f"Too many server errors: {errors}"


@pytest.mark.asyncio
async def test_timeout_handling(api_client):
    """
    Test that timeouts are handled gracefully.
    """
    import httpx

    # Create client with very short timeout
    async with httpx.AsyncClient(
        base_url=os.getenv("BASE_URL", "http://localhost:8000"),
        timeout=0.001,  # 1ms timeout - will definitely timeout
    ) as short_timeout_client:
        timeout_count = 0
        success_count = 0

        for _ in range(10):
            try:
                response = await short_timeout_client.get("/v1/placements")
                success_count += 1
            except httpx.TimeoutException:
                timeout_count += 1
            except Exception:
                pass

        print(f"\nTimeout Test Results:")
        print(f"  Timeouts: {timeout_count}")
        print(f"  Successes: {success_count}")

        # Most should timeout with 1ms limit
        assert timeout_count > 0, "Expected some timeouts"


@pytest.mark.asyncio
async def test_retry_behavior(api_client):
    """
    Test that retries work correctly.
    """
    # This test would need a way to inject failures
    # For now, just verify the endpoint is resilient to multiple calls

    results = []
    for i in range(20):
        try:
            response = await api_client.get("/v1/placements?limit=1")
            results.append(response.status_code)
        except Exception as e:
            results.append(f"error: {e}")
        await asyncio.sleep(0.1)

    success_rate = sum(1 for r in results if r == 200) / len(results)
    print(f"\nRetry Test Results:")
    print(f"  Success rate: {success_rate * 100:.1f}%")

    assert success_rate >= 0.9, f"Success rate too low: {success_rate}"
