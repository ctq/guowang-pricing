import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    allowedHosts: ['bid.zkhj.cc'],
    proxy: {
      '/api': process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8000',
      '/health': process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8000',
    },
  },
})
