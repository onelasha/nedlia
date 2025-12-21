/**
 * Nedlia API Stress Test
 *
 * Find breaking point by ramping up load until failure.
 * Run: k6 run stress-test.js
 */

import { check, sleep } from 'k6';
import http from 'k6/http';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '2m', target: 50 }, // Warm up
    { duration: '5m', target: 100 }, // Normal load
    { duration: '5m', target: 200 }, // High load
    { duration: '5m', target: 500 }, // Stress
    { duration: '5m', target: 1000 }, // Breaking point
    { duration: '5m', target: 0 }, // Recovery
  ],
  thresholds: {
    http_req_duration: ['p(99)<2000'], // Relaxed for stress test
    errors: ['rate<0.1'], // Allow up to 10% errors
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  const res = http.get(`${BASE_URL}/v1/placements?limit=20`);

  const success = check(res, {
    'status is 200': r => r.status === 200,
  });

  errorRate.add(!success);
  sleep(0.1);
}
