const request = require('supertest');
const app = require('../src/app');

describe('PhoenixCI Express Endpoints', () => {
  test('GET / returns 200 and project information', async () => {
    const res = await request(app).get('/');
    expect(res.statusCode).toBe(200);
    expect(res.body.project).toBe('PhoenixCI');
    expect(res.body.status).toBe('operational');
    expect(res.body.version).toBe('1.0.0');
  });

  test('GET /health returns 200 and ok status', async () => {
    const res = await request(app).get('/health');
    expect(res.statusCode).toBe(200);
    expect(res.body.status).toBe('ok');
    expect(res.body).toHaveProperty('timestamp');
    expect(res.body).toHaveProperty('uptime');
  });

  test('GET /api/status returns 200 with runtime info', async () => {
    const res = await request(app).get('/api/status');
    expect(res.statusCode).toBe(200);
    expect(res.body.status).toBe('healthy');
    expect(res.body.version).toBe('1.0.0');
    expect(res.body).toHaveProperty('nodeVersion');
  });

  test('POST /api/priority calculates priority correctly', async () => {
    const res = await request(app)
      .post('/api/priority')
      .send({ severity: 'critical', affectedUsers: 10 });
    expect(res.statusCode).toBe(200);
    expect(res.body.priority).toBe('P1');
  });

  test('POST /api/priority returns 400 for invalid payload', async () => {
    const res = await request(app)
      .post('/api/priority')
      .send({ severity: 'invalid_level', affectedUsers: 10 });
    expect(res.statusCode).toBe(400);
    expect(res.body).toHaveProperty('error');
  });
});
