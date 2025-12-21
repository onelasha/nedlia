# Performance Tests

Performance testing suite for Nedlia's event-driven architecture.

## Structure

```
tools/performance-tests/
├── README.md                 # This file
├── k6/                       # k6 load tests
│   ├── load-test.js          # Standard load test
│   ├── stress-test.js        # Stress/breaking point test
│   ├── spike-test.js         # Spike test
│   └── soak-test.js          # Endurance test
├── consistency/              # Eventual consistency tests
│   ├── consistency_test.py   # Consistency SLO validation
│   └── conftest.py           # Pytest fixtures
├── producers/                # Event producers for load testing
│   └── event_producer.py     # EventBridge event producer
├── chaos/                    # Chaos engineering tests
│   ├── cold_start_test.py    # Lambda cold start testing
│   ├── backpressure_test.py  # Backpressure & failure testing
│   └── idempotency_test.py   # Idempotency validation
├── reports/                  # Test reports (gitignored)
└── pyproject.toml            # Python dependencies
```

## Quick Start

```bash
# Install dependencies
cd tools/performance-tests
uv sync

# Run k6 load test
k6 run k6/load-test.js

# Run consistency tests
uv run pytest consistency/ -v

# Run chaos tests
uv run pytest chaos/ -v
```

## Test Types

| Test        | Command                    | Duration | When to Run |
| ----------- | -------------------------- | -------- | ----------- |
| Load        | `k6 run k6/load-test.js`   | 15 min   | Nightly     |
| Stress      | `k6 run k6/stress-test.js` | 30 min   | Weekly      |
| Spike       | `k6 run k6/spike-test.js`  | 10 min   | Weekly      |
| Soak        | `k6 run k6/soak-test.js`   | 4 hours  | Weekly      |
| Consistency | `pytest consistency/`      | 10 min   | Every PR    |
| Chaos       | `pytest chaos/`            | 30 min   | Monthly     |

## Environment Variables

```bash
export BASE_URL=https://api.staging.nedlia.com
export AWS_REGION=us-east-1
export EVENTBRIDGE_BUS=nedlia-events
```

## Reports

Reports are generated in `reports/` directory:

- `summary.json` - k6 summary
- `consistency_report.json` - Consistency test results
- `performance_report.md` - Full markdown report
