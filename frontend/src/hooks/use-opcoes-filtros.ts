import { useQuery } from '@tanstack/react-query'
import type { ClasseConsumo } from '@/config/classes'
import { apiFetch } from '@/lib/api/api-fetch'

// Formato proposto para GET /api/filters/options (a validar com o backend)
export type OpcoesFiltros = {
  // Meses da base em ordem crescente, no formato yyyy-MM
  competencias: string[]
  municipios: { nome: string; bairros: string[] }[]
  classes: ClasseConsumo[]
}

// As opções só mudam quando o pipeline roda: busca uma vez e guarda
export function useOpcoesFiltros() {
  return useQuery({
    queryKey: ['filtros', 'opcoes'],
    queryFn: ({ signal }) => apiFetch<OpcoesFiltros>('/filters/options', { signal }),
    staleTime: Infinity,
  })
}
