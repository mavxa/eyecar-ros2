import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    proxy: {
      '/api/ws': {
        target: 'ws://127.0.0.1:9090',
        ws: true,
      },
    },
  },
});
