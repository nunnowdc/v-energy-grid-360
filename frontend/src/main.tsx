import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Dados de exemplo só no npm run dev, e só se ligados no .env.local.
// No build de produção este trecho é removido
async function iniciarDadosExemplo() {
  if (!import.meta.env.DEV || import.meta.env.VITE_USAR_DADOS_EXEMPLO !== 'true') {
    return
  }

  const { worker } = await import('./mocks/browser')
  // Rotas sem exemplo (ex.: /api/health) seguem para o backend de verdade
  await worker.start({ onUnhandledRequest: 'bypass' })
}

await iniciarDadosExemplo()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
