import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      // Audio and diagram files are served directly by Flask outside /api.
      // Without this proxy entry the browser requests them from Vite (port 5173)
      // which has no /audio route, returning a 404 and a 0-byte response.
      // That is why duration shows 0:00 and the player cannot play.
      '/audio': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/diagrams': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
});
