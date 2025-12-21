/**
 * Nedlia API Load Test
 *
 * Standard load test for API endpoints.
 * Run: k6 run load-test.js
 * With env: k6 run -e BASE_URL=https://api.staging.nedlia.com load-test.js
 */

import { randomUUID } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';
import { check, sleep } from 'k6';
import http from 'k6/http';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const placementDuration = new Trend('placement_duration');
const consistencyLatency = new Trend('consistency_latency');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 50 }, // Ramp up to 50 users
    { duration: '5m', target: 50 }, // Stay at 50
    { duration: '2m', target: 100 }, // Ramp up to 100
    { duration: '5m', target: 100 }, // Stay at 100
    { duration: '2m', target: 0 }, // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    errors: ['rate<0.01'],
    consistency_latency: ['p(95)<2000'], // 95% consistent within 2s
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  const correlationId = randomUUID();

  // 1. Create placement
  const createStart = Date.now();
  const createRes = http.post(
    `${BASE_URL}/v1/placements`,
    JSON.stringify({
      video_id: '550e8400-e29b-41d4-a716-446655440000',
      product_id: '6ba7b810-9dad-11d1-80b4-00c04fd430c8',
      time_range: { start_time: Math.random() * 100, end_time: Math.random() * 100 + 100 },
      _correlation_id: correlationId,
    }),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { name: 'CreatePlacement' },
    }
  );

  const createSuccess = check(createRes, {
    'create status is 201': r => r.status === 201,
    'create has id': r => JSON.parse(r.body).data?.id !== undefined,
  });
  errorRate.add(!createSuccess);
  placementDuration.add(Date.now() - createStart);

  if (!createSuccess) {
    return;
  }

  const placementId = JSON.parse(createRes.body).data.id;

  sleep(0.5);

  // 2. Poll for consistency (file_url populated by async worker)
  const consistencyStart = Date.now();
  let consistent = false;
  let pollCount = 0;
  const maxPolls = 20; // 2 seconds max (100ms * 20)

  while (!consistent && pollCount < maxPolls) {
    sleep(0.1);
    pollCount++;

    const getRes = http.get(`${BASE_URL}/v1/placements/${placementId}`, {
      tags: { name: 'GetPlacement' },
    });

    if (getRes.status === 200) {
      const data = JSON.parse(getRes.body).data;
      if (data.file_url) {
        consistent = true;
      }
    }
  }

  consistencyLatency.add(Date.now() - consistencyStart);

  check(null, {
    'eventually consistent': () => consistent,
  });

  sleep(1);

  // 3. List placements
  const listRes = http.get(`${BASE_URL}/v1/placements?limit=20`, {
    tags: { name: 'ListPlacements' },
  });

  check(listRes, {
    'list status is 200': r => r.status === 200,
    'list has data': r => JSON.parse(r.body).data !== undefined,
  });

  sleep(1);
}

export function handleSummary(data) {
  return {
    'reports/summary.json': JSON.stringify(data, null, 2),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function textSummary(data, options) {
  // Simple text summary
  const metrics = data.metrics;
  return `
=== Nedlia Load Test Summary ===

Requests:
  Total: ${metrics.http_reqs?.values?.count || 0}
  Rate: ${metrics.http_reqs?.values?.rate?.toFixed(2) || 0}/s

Latency:
  P50: ${metrics.http_req_duration?.values?.['p(50)']?.toFixed(2) || 0}ms
  P95: ${metrics.http_req_duration?.values?.['p(95)']?.toFixed(2) || 0}ms
  P99: ${metrics.http_req_duration?.values?.['p(99)']?.toFixed(2) || 0}ms

Consistency:
  P95: ${metrics.consistency_latency?.values?.['p(95)']?.toFixed(2) || 0}ms

Errors: ${(metrics.errors?.values?.rate * 100)?.toFixed(2) || 0}%

Thresholds: ${
    data.thresholds
      ? Object.entries(data.thresholds)
          .map(([k, v]) => `${k}: ${v.ok ? '✅' : '❌'}`)
          .join(', ')
      : 'N/A'
  }
`;
}
