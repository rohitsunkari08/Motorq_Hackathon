import http from 'k6/http';
import { check, sleep } from 'k6';

// k6 load test configuration per NOTE.md §9 / §15 / §16
export const options = {
  stages: [
    { duration: '5s', target: 25 },    // ramp-up
    { duration: '20s', target: 50 },   // steady load
    { duration: '5s', target: 0 },     // ramp-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<200', 'p(99)<500'], // p95 < 200ms, p99 < 500ms per NOTE.md §1 & §15
    http_req_failed: ['rate<0.01'],               // < 1% error rate
  },
};

const BASE_URL = __ENV.API_URL || 'http://localhost:8000';

export function setup() {
  // Pre-login as admin to obtain JWT (admin role exempt from rate limits for benchmark)
  const loginRes = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ email: 'admin@voltfleet.com', password: 'Password123!' }),
    { headers: { 'Content-Type': 'application/json' } }
  );

  check(loginRes, {
    'login status is 200': (r) => r.status === 200,
  });

  const body = JSON.parse(loginRes.body);
  return { token: body.access_token };
}

export default function (data) {
  const params = {
    headers: {
      Authorization: `Bearer ${data.token}`,
      'Content-Type': 'application/json',
      Connection: 'keep-alive',
    },
  };

  // Mixed read workload: Fleet vehicles keyset, fleet summary, vehicle detail
  const actions = [
    () => {
      const res = http.get(`${BASE_URL}/api/v1/fleets/1/vehicles?limit=20`, params);
      check(res, { 'status 200': (r) => r.status === 200 });
    },
    () => {
      const res = http.get(`${BASE_URL}/api/v1/fleets/1/summary`, params);
      check(res, { 'status 200': (r) => r.status === 200 });
    },
    () => {
      const res = http.get(`${BASE_URL}/api/v1/vehicles/1VXEV01A100000001`, params);
      check(res, { 'status 200': (r) => r.status === 200 });
    },
    () => {
      const res = http.get(`${BASE_URL}/health`);
      check(res, { 'health 200': (r) => r.status === 200 });
    },
  ];

  // Pick random action
  const action = actions[Math.floor(Math.random() * actions.length)];
  action();

  sleep(0.1); // pacing
}
