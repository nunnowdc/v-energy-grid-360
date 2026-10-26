import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router'
import type { OpcoesFiltros } from '@/hooks/use-opcoes-filtros'

type OpcoesRenderizar = {
  // Endereço inicial da tela, ex.: "/receita?municipio=Recife"
  url?: string
  // Opções dos filtros já no cache, sem precisar do backend
  opcoesFiltros?: OpcoesFiltros
}

// Renderiza com os mesmos provedores do portal: cache de consultas novo a cada
// teste (sem nova tentativa, para o erro aparecer na hora) e rotas em memória
export function renderizar(ui: ReactNode, { url = '/', opcoesFiltros }: OpcoesRenderizar = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  if (opcoesFiltros) {
    queryClient.setQueryData(['filtros', 'opcoes'], opcoesFiltros)
  }

  const comProvedores = (conteudo: ReactNode) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[url]}>{conteudo}</MemoryRouter>
    </QueryClientProvider>
  )

  const resultado = render(comProvedores(ui))

  return {
    ...resultado,
    queryClient,
    // Re-renderiza mantendo os mesmos provedores (e o mesmo cache)
    rerender: (novaUi: ReactNode) => resultado.rerender(comProvedores(novaUi)),
  }
}
