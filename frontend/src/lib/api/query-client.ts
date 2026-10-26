import { MutationCache, QueryCache, QueryClient } from '@tanstack/react-query'
import { ErroApi } from '@/lib/api/erro-api'
import { tratarSessaoExpirada } from '@/lib/api/sessao'

// Configuração padrão de todas as consultas do portal
export const queryClient = new QueryClient({
  // Qualquer consulta ou alteração que receber 401 leva ao login
  // (a função anônima evita passar a consulta como segundo argumento)
  queryCache: new QueryCache({ onError: (erro) => tratarSessaoExpirada(erro) }),
  mutationCache: new MutationCache({ onError: (erro) => tratarSessaoExpirada(erro) }),
  defaultOptions: {
    queries: {
      // As tabelas Gold do MVP são um retrato fixo, então
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
