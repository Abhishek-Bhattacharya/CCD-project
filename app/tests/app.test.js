const request = require('supertest');
const app = require('../src/app');

describe('PhoenixCI Express Endpoints', () => {
  test('GET / returns 200 and project information', async () => {
    const res = await request(app).get('/');
    expect(res.statusCode).toBe(200);
    expect(res.body.project).toBe('PhoenixCI');
    expect(res.body.app).toBe('Foundly');
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

  test('GET /runtime-config.js returns frontend Supabase configuration', async () => {
    const originalUrl = process.env.VITE_SUPABASE_URL;
    const originalKey = process.env.VITE_SUPABASE_ANON_KEY;
    process.env.VITE_SUPABASE_URL = 'https://example.supabase.co';
    process.env.VITE_SUPABASE_ANON_KEY = 'test-public-key';

    try {
      const res = await request(app).get('/runtime-config.js');
      expect(res.statusCode).toBe(200);
      expect(res.headers['content-type']).toMatch(/javascript/);
      expect(res.headers['cache-control']).toBe('no-store');
      expect(res.text).toContain('"supabaseUrl":"https://example.supabase.co"');
      expect(res.text).toContain('"supabaseAnonKey":"test-public-key"');
    } finally {
      if (originalUrl === undefined) delete process.env.VITE_SUPABASE_URL;
      else process.env.VITE_SUPABASE_URL = originalUrl;
      if (originalKey === undefined) delete process.env.VITE_SUPABASE_ANON_KEY;
      else process.env.VITE_SUPABASE_ANON_KEY = originalKey;
    }
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
