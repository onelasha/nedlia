/**
 * Nedlia API Spike Test
 *
 * Test sudden traffic bursts and recovery.
 * Run: k6 run spike-test.js
 */

import { check, sleep } from 'k6';
import http from 'k6/http';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '1m', target: 10 }, // Baseline
    { duration: '10s', target: 500 }, // Spike!
    { duration: '3m', target: 500 }, // Stay at spike
    { duration: '10s', target: 10 }, // Scale down
    { duration: '3m', target: 10 }, // Recovery
    { duration: '10s', target: 800 }, // Another spike
    { duration: '3m', target: 800 }, // Stay
    { duration: '1m', target: 0 }, // Scale down
  ],
  thresholds: {
    http_req_duration: ['p(95)<1000'],
    errors: ['rate<0.05'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  const res = http.get(`${BASE_URL}/v1/placements?limit=20`);

  const success = check(res, {
    'status is 200 or 429': r => r.status === 200 || r.status === 429,
  });

  errorRate.add(res.status >= 500);
  sleep(0.1);
}
