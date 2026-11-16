import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', 'VITE_');
  const apiTarget = env.VITE_API_TARGET || 'http://127.0.0.1:8000';
  return {
    plugins: [react(), tailwindcss()],
    server: {
      host: '0.0.0.0',
      port: 5173,
      allowedHosts: true,
      proxy: {
        '/api': { target: apiTarget, changeOrigin: true },
        '/iceberg-price-radar.git': { target: apiTarget, changeOrigin: true },
      },
    },
  };
});
