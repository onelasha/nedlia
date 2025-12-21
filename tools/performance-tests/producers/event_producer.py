"""
Event Producer for Load Testing

Produces events at controlled rate for testing event-driven flows.
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

import boto3


@dataclass
class ProducerConfig:
    events_per_second: int
    duration_seconds: int
    event_type: str = "placement.created"
    ramp_up_seconds: int = 60
    event_bus_name: str = "nedlia-events"


@dataclass
class ProducerReport:
    test_run_id: str
    total_events: int
    target_rate: int
    actual_rate: float
    duration_seconds: float
    errors: int = 0


class EventProducer:
    """Produces events at controlled rate for load testing."""

    def __init__(self, config: ProducerConfig):
        self.config = config
        self.eventbridge = boto3.client(
            "events",
            endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
            region_name=os.getenv("AWS_REGION", "us-east-1"),
        )
        self.test_run_id = f"perf_{int(time.time())}"
        self.produced_events = []
        self.errors = 0

    async def run(self) -> ProducerReport:
        """Run the load test."""
        total_events = self.config.events_per_second * self.config.duration_seconds

        print(f"Starting load test: {self.config.events_per_second} events/sec")
        print(f"Duration: {self.config.duration_seconds}s")
        print(f"Test run ID: {self.test_run_id}")

        start_time = time.time()
        events_sent = 0

        while events_sent < total_events:
            elapsed = time.time() - start_time

            # Ramp up logic
            if elapsed < self.config.ramp_up_seconds:
                current_rate = max(
                    1,
                    self.config.events_per_second
                    * (elapsed / self.config.ramp_up_seconds),
                )
            else:
                current_rate = self.config.events_per_second

            interval = 1.0 / current_rate

            event = self._create_event()
            success = await self._publish_event(event)

            if success:
                self.produced_events.append(event)
            else:
                self.errors += 1

            events_sent += 1

            # Sleep to maintain rate
            await asyncio.sleep(interval)

            # Progress update every 10 seconds
            if events_sent % (self.config.events_per_second * 10) == 0:
                print(f"  Sent {events_sent}/{total_events} events...")

        end_time = time.time()
        actual_duration = end_time - start_time

        return ProducerReport(
            test_run_id=self.test_run_id,
            total_events=len(self.produced_events),
            target_rate=self.config.events_per_second,
            actual_rate=len(self.produced_events) / actual_duration,
            duration_seconds=actual_duration,
            errors=self.errors,
        )

    def _create_event(self) -> dict:
        return {
            "id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "test_run_id": self.test_run_id,
            "type": self.config.event_type,
            "produced_at": time.time(),
            "produced_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            "data": {
                "video_id": str(uuid4()),
                "product_id": str(uuid4()),
                "time_range": {"start_time": 0, "end_time": 30},
            },
        }

    async def _publish_event(self, event: dict) -> bool:
        try:
            self.eventbridge.put_events(
                Entries=[
                    {
                        "Source": "nedlia.perf-test",
                        "DetailType": event["type"],
                        "Detail": json.dumps(event),
                        "EventBusName": self.config.event_bus_name,
                    }
                ]
            )
            return True
        except Exception as e:
            print(f"Error publishing event: {e}")
            return False


async def main():
    """Run event producer."""
    config = ProducerConfig(
        events_per_second=int(os.getenv("EVENTS_PER_SECOND", "100")),
        duration_seconds=int(os.getenv("DURATION_SECONDS", "300")),
        event_type=os.getenv("EVENT_TYPE", "placement.created"),
        ramp_up_seconds=int(os.getenv("RAMP_UP_SECONDS", "60")),
    )

    producer = EventProducer(config)
    report = await producer.run()

    print("\n=== Event Producer Report ===")
    print(f"Test Run ID: {report.test_run_id}")
    print(f"Total Events: {report.total_events}")
    print(f"Target Rate: {report.target_rate}/s")
    print(f"Actual Rate: {report.actual_rate:.2f}/s")
    print(f"Duration: {report.duration_seconds:.2f}s")
    print(f"Errors: {report.errors}")


if __name__ == "__main__":
    asyncio.run(main())
