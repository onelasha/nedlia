"""
Eventual Consistency Tests

Validates that the system reaches consistent state within SLO.
"""

import asyncio
import json
import time
from pathlib import Path
from uuid import uuid4

import pytest


class ConsistencyTester:
    """Validates eventual consistency SLOs."""

    def __init__(self, api_client, slo_seconds: float = 5.0):
        self.api = api_client
        self.slo = slo_seconds
        self.results = []

    async def test_placement_consistency(self, num_events: int = 100):
        """
        1. Create placement via API
        2. Poll read model until consistent
        3. Record consistency latency
        """
        tasks = [self._single_consistency_test() for _ in range(num_events)]
        self.results = await asyncio.gather(*tasks, return_exceptions=True)
        # Filter out exceptions
        self.results = [r for r in self.results if isinstance(r, dict)]
        return self._analyze_results()

    async def _single_consistency_test(self) -> dict:
        correlation_id = str(uuid4())
        start_time = time.time()

        # 1. Write via API
        response = await self.api.post(
            "/v1/placements",
            json={
                "video_id": "550e8400-e29b-41d4-a716-446655440000",
                "product_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                "time_range": {"start_time": 0, "end_time": 10},
                "_correlation_id": correlation_id,
            },
        )

        if response.status_code != 201:
            return {
                "correlation_id": correlation_id,
                "error": f"Create failed: {response.status_code}",
                "consistent": False,
                "within_slo": False,
            }

        placement_id = response.json()["data"]["id"]
        write_time = time.time()

        # 2. Poll read model until consistent
        consistent = False
        poll_count = 0
        max_polls = int(self.slo * 10)  # Poll every 100ms

        while not consistent and poll_count < max_polls:
            await asyncio.sleep(0.1)
            poll_count += 1

            try:
                placement = await self.api.get(f"/v1/placements/{placement_id}")
                if placement.status_code == 200:
                    data = placement.json().get("data", {})
                    # Check if file_url is populated (set by async worker)
                    if data.get("file_url"):
                        consistent = True
            except Exception:
                pass

        end_time = time.time()

        return {
            "correlation_id": correlation_id,
            "placement_id": placement_id,
            "write_latency_ms": (write_time - start_time) * 1000,
            "consistency_latency_ms": (end_time - start_time) * 1000,
            "consistent": consistent,
            "within_slo": (end_time - start_time) <= self.slo,
            "poll_count": poll_count,
        }

    def _analyze_results(self) -> dict:
        if not self.results:
            return {"error": "No results"}

        latencies = [
            r["consistency_latency_ms"] for r in self.results if r.get("consistent")
        ]

        if not latencies:
            return {
                "total_events": len(self.results),
                "consistent_count": 0,
                "slo_percentage": 0,
                "error": "No events reached consistency",
            }

        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        return {
            "total_events": len(self.results),
            "consistent_count": sum(1 for r in self.results if r.get("consistent")),
            "within_slo_count": sum(1 for r in self.results if r.get("within_slo")),
            "slo_percentage": sum(1 for r in self.results if r.get("within_slo"))
            / len(self.results)
            * 100,
            "p50_latency_ms": sorted_latencies[n // 2],
            "p90_latency_ms": sorted_latencies[int(n * 0.9)],
            "p99_latency_ms": sorted_latencies[int(n * 0.99)] if n > 100 else sorted_latencies[-1],
            "max_latency_ms": max(latencies),
            "min_latency_ms": min(latencies),
        }


@pytest.mark.asyncio
async def test_placement_consistency_slo(api_client, slo_seconds):
    """Test that 95% of placements reach consistency within SLO."""
    tester = ConsistencyTester(api_client, slo_seconds)
    results = await tester.test_placement_consistency(num_events=50)

    # Save report
    report_path = Path(__file__).parent.parent / "reports"
    report_path.mkdir(exist_ok=True)
    with open(report_path / "consistency_report.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nConsistency Test Results:")
    print(f"  Total events: {results['total_events']}")
    print(f"  Consistent: {results['consistent_count']}")
    print(f"  Within SLO: {results['within_slo_count']}")
    print(f"  SLO %: {results['slo_percentage']:.1f}%")
    print(f"  P50 latency: {results.get('p50_latency_ms', 'N/A')}ms")
    print(f"  P99 latency: {results.get('p99_latency_ms', 'N/A')}ms")

    # Assert SLO: 95% within threshold
    assert results["slo_percentage"] >= 95, (
        f"Consistency SLO not met: {results['slo_percentage']:.1f}% < 95%"
    )


@pytest.mark.asyncio
async def test_write_latency(api_client):
    """Test that write latency is acceptable."""
    tester = ConsistencyTester(api_client)
    results = await tester.test_placement_consistency(num_events=20)

    write_latencies = [
        r["write_latency_ms"] for r in tester.results if "write_latency_ms" in r
    ]

    if write_latencies:
        p99_write = sorted(write_latencies)[int(len(write_latencies) * 0.99)]
        print(f"\nWrite Latency P99: {p99_write:.2f}ms")
        assert p99_write < 500, f"Write latency too high: {p99_write}ms"
