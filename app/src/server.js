const app = require('./app');

const PORT = process.env.PORT || 3000;

const server = app.listen(PORT, () => {
  console.log(`[PhoenixCI Service] Running on port ${PORT}`);
});

process.on('SIGTERM', () => {
  console.log('[PhoenixCI Service] Received SIGTERM, shutting down gracefully...');
  server.close(() => {
    process.exit(0);
  });
});

module.exports = server;
