const express = require('express');
const { calculateIncidentPriority } = require('./priority');

const app = express();
app.use(express.json());

// Root endpoint: project information & version
app.get('/', (req, res) => {
  res.status(200).json({
    project: 'PhoenixCI',
    description: 'Groq-Powered Self-Healing CI/CD Pipeline',
    version: '1.0.0',
    status: 'operational'
  });
});

// Health check endpoint
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
    nodeVersion: process.version,
    environment: process.env.NODE_ENV || 'development'
  });
});

// Business logic endpoint: incident priority triage
app.post('/api/priority', (req, res) => {
  try {
    const { severity, affectedUsers, isProduction } = req.body;
    const priority = calculateIncidentPriority(severity, affectedUsers, isProduction);
    res.status(200).json({ priority });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

module.exports = app;
