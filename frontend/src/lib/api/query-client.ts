import { QueryClient } from '@tanstack/react-query'
import { ErroApi } from '@/lib/api/erro-api'

// Configuração padrão de todas as consultas do portal
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Os dados da Gold só mudam quando o pipeline roda (mensal), então
      // 5 minutos de cache evitam buscas repetidas ao trocar de tela
      staleTime: 5 * 60 * 1000,
      refetchOnWindowFocus: false,
      // Erros 4xx não melhoram tentando de novo; falhas de rede e 5xx tentam mais 1 vez
      retry: (falhas, erro) => {
        const erroDoCliente = erro instanceof ErroApi && erro.status >= 400 && erro.status < 500
        return !erroDoCliente && falhas < 1
      },
    },
  },
})
