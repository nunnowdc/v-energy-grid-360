/// <reference types="vitest/config" />
import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Em desenvolvimento, as chamadas para /api vão para o FastAPI. Assim o navegador
// vê um único endereço e o cookie de login funciona sem precisar de CORS
const proxy = {
  '/api': 'http://127.0.0.1:8000',
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  // Porta fixa: o backend só aceita escritas vindas de localhost:5173 ou
  // 127.0.0.1:5173. Se ela estiver ocupada, o Vite para com erro em vez de
  // subir em outra porta, onde o login e as ordens dariam 403
  server: { proxy, port: 5173, strictPort: true },
  preview: { proxy },
  // Testes automatizados (npm test): navegador simulado com jsdom
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
})

