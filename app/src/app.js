const express = require('express');
const path = require('path');
const { calculateIncidentPriority } = require('./priority');

const app = express();
app.use(express.json());

app.get('/runtime-config.js', (req, res) => {
  const config = {
    supabaseUrl: process.env.VITE_SUPABASE_URL || process.env.SUPABASE_URL || '',
    supabaseAnonKey: process.env.VITE_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY || ''
  };

  res
    .type('application/javascript')
    .set('Cache-Control', 'no-store')
    .send(`window.__FOUNDLY_CONFIG__ = ${JSON.stringify(config)};`);
});

// ─── Serve static Vite build in production ────────────────────────────────────
// In dev, Vite runs on port 5173 and proxies /api/* and /health to this server.
// In production (Docker / CI), Express serves the Vite dist/ directory.
const DIST_DIR = path.join(__dirname, '..', 'dist');

if (process.env.NODE_ENV === 'production') {
  app.use(express.static(DIST_DIR));
}

// ─── API Routes (always available) ────────────────────────────────────────────

// Health check endpoint (used by PhoenixCI and Docker healthcheck)
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

// System status endpoint
app.get('/api/status', (req, res) => {
  res.status(200).json({
    status: 'healthy',
    version: '1.0.0',
    app: 'Foundly',
    nodeVersion: process.version,
    environment: process.env.NODE_ENV || 'development'
  });
});

// Business logic endpoint: incident priority triage (PhoenixCI target)
app.post('/api/priority', (req, res) => {
  try {
    const { severity, affectedUsers, isProduction } = req.body;
    const priority = calculateIncidentPriority(severity, affectedUsers, isProduction);
    res.status(200).json({ priority });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// ─── SPA Fallback: serve index.html for all non-API routes in production ──────
if (process.env.NODE_ENV === 'production') {
  app.get('*', (req, res, next) => {
    // Don't intercept API or health routes
    if (req.path.startsWith('/api/') || req.path === '/health') {
      return next();
    }
    res.sendFile(path.join(DIST_DIR, 'index.html'));
  });
} else {
  // Dev fallback: keep a JSON root response so supertest still passes
  app.get('/', (req, res) => {
    res.status(200).json({
      project: 'PhoenixCI / Foundly',
      description: 'Groq-Powered Self-Healing CI/CD Pipeline — Campus Lost & Found',
      version: '1.0.0',
      status: 'operational'
    });
  });
}

module.exports = app;
