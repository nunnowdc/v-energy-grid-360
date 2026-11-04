import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterEach } from 'vitest'

// findBy e waitFor esperam até 3 s (o padrão é 1 s): em máquina lenta ou ocupada,
// a tela pode demorar mais que isso para aparecer. Teste que passa não fica mais lento
configure({ asyncUtilTimeout: 3000 })

// Desmonta o que cada teste renderizou, para um não interferir no outro
afterEach(() => {
  cleanup()
})

// O jsdom não tem matchMedia, que o menu lateral usa para saber se a tela é de celular
window.matchMedia ??= ((query: string) => ({
  matches: false,
  media: query,
  onchange: null,
  addEventListener: () => {},
  removeEventListener: () => {},
  addListener: () => {},
  removeListener: () => {},
  dispatchEvent: () => false,
})) as typeof window.matchMedia
