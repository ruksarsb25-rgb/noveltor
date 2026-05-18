import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      '/parse': 'http://localhost:5001',
      '/generate': 'http://localhost:5001',
      '/validate': 'http://localhost:5001',
      '/autotag': 'http://localhost:5001',
      '/health': 'http://localhost:5001',
      '/export': 'http://localhost:5001',
      '/preview': 'http://localhost:5001',
    },
  },
})
