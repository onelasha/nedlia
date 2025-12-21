/**
 * Nedlia API Soak Test
 *
 * Long-running test to detect memory leaks and resource exhaustion.
 * Run: k6 run soak-test.js
 */

import { check, sleep } from 'k6';
import http from 'k6/http';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const latencyTrend = new Trend('latency_over_time');

export const options = {
  stages: [
    { duration: '5m', target: 50 }, // Ramp up
    { duration: '4h', target: 50 }, // Sustained load for 4 hours
    { duration: '5m', target: 0 }, // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    errors: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  const start = Date.now();

  const res = http.get(`${BASE_URL}/v1/placements?limit=20`);

  latencyTrend.add(Date.now() - start);

  const success = check(res, {
    'status is 200': r => r.status === 200,
  });

  errorRate.add(!success);
  sleep(1);
}
