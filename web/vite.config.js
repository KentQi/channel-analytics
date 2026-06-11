import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 8502,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        // dev 期 vite proxy 从本机发起，改 127.0.0.1 走 loopback，不走局域网网卡。
        // 配合 start_backend.bat 的 --host 127.0.0.1，局域网用户无法直接访问 8602。
        target: 'http://127.0.0.1:8602',
        changeOrigin: true
      }
    }
  }
})
