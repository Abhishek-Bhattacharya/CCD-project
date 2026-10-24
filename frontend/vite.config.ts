import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': 'http://localhost:3000',
      '/health': 'http://localhost:3000',
      '/runtime-config.js': 'http://localhost:3000',
    },
  },
  build: {
    outDir: '../app/dist',
    emptyOutDir: true,
  },
});