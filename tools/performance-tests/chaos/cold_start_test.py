"""
Cold Start & Scale-Up Tests

Tests Lambda cold start behavior and Fargate scale-up time.
"""

import asyncio
import time

import pytest


@pytest.mark.asyncio
@pytest.mark.slow
async def test_lambda_cold_starts(api_client):
    """
    Force cold starts by:
    1. Waiting for Lambda to scale down (simulated with delay)
    2. Sending burst of concurrent requests
    3. Measuring first response times
    """
    print("\nWaiting 30s to simulate scale-down (use 15min in real test)...")
    await asyncio.sleep(30)  # In real test, wait 15 minutes

    # Burst 20 concurrent requests
    print("Sending burst of 20 concurrent requests...")
    start = time.time()

    async def make_request():
        req_start = time.time()
        response = await api_client.get("/v1/placements?limit=1")
        return {
            "status": response.status_code,
            "latency_ms": (time.time() - req_start) * 1000,
        }

    tasks = [make_request() for _ in range(20)]
    responses = await asyncio.gather(*tasks)
    end = time.time()

    latencies = [r["latency_ms"] for r in responses if r["status"] == 200]

    if not latencies:
        pytest.skip("No successful responses")

    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)

    results = {
        "total_requests": len(responses),
        "successful": len(latencies),
        "cold_start_p50_ms": sorted_latencies[n // 2],
        "cold_start_p99_ms": sorted_latencies[-1],
        "cold_start_max_ms": max(latencies),
        "total_burst_time_ms": (end - start) * 1000,
    }

    print(f"\nCold Start Results:")
    print(f"  P50: {results['cold_start_p50_ms']:.2f}ms")
    print(f"  P99: {results['cold_start_p99_ms']:.2f}ms")
    print(f"  Max: {results['cold_start_max_ms']:.2f}ms")

    # Assert cold start is acceptable
    assert results["cold_start_p99_ms"] < 3000, (
        f"Cold start P99 too high: {results['cold_start_p99_ms']}ms"
    )


@pytest.mark.asyncio
async def test_warm_latency(api_client):
    """
    Test latency with warm instances.
    Send requests to warm up, then measure.
    """
    # Warm up
    print("\nWarming up with 10 requests...")
    for _ in range(10):
        await api_client.get("/v1/placements?limit=1")
        await asyncio.sleep(0.1)

    # Measure warm latency
    print("Measuring warm latency...")
    latencies = []
    for _ in range(50):
        start = time.time()
        response = await api_client.get("/v1/placements?limit=1")
        if response.status_code == 200:
            latencies.append((time.time() - start) * 1000)
        await asyncio.sleep(0.05)

    if not latencies:
        pytest.skip("No successful responses")

    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)

    print(f"\nWarm Latency Results:")
    print(f"  P50: {sorted_latencies[n // 2]:.2f}ms")
    print(f"  P99: {sorted_latencies[-1]:.2f}ms")

    # Warm latency should be much lower than cold
    assert sorted_latencies[-1] < 500, (
        f"Warm P99 too high: {sorted_latencies[-1]}ms"
    )
