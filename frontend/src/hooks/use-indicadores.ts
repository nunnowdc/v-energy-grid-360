import { keepPreviousData, useQuery } from '@tanstack/react-query'
import type { ClasseConsumo } from '@/config/classes'
import { useOpcoesFiltros } from '@/hooks/use-opcoes-filtros'
import { apiFetch } from '@/lib/api/api-fetch'
import { periodosComparados, type Filtros } from '@/lib/filtros-url'

// Formato de GET /api/metrics/general?inicio=&fim=&inicio_anterior=&fim_anterior=&municipio=&classe=
// (meses yyyy-MM), igual ao backend/app/schemas/metrics.py. Tudo vem de agg_receita_mensal, somado
// no recorte pedido. Os dois períodos têm o mesmo tamanho (1 a 24 meses) e o anterior termina antes
// de "inicio"; sem inicio_anterior e fim_anterior, o backend usa o imediatamente anterior

// Totais de um período
export type ResumoIndicadores = {
  inicio: string
  fim: string
  receita_faturada: number
  consumo_kwh: number
  // receita_faturada ÷ consumo_kwh do período (mesma fórmula da Gold); nulo sem consumo
  preco_medio_kwh: number | null
  // UCs com fatura no ÚLTIMO mês do período (não é soma entre meses)
  ucs_faturadas: number
  faturas: number
  faturas_atrasadas: number
}

export type MesIndicadores = {
  mes_referencia: string
  receita_faturada: number
  consumo_kwh: number
}

export type IndicadoresGerais = {
  atual: ResumoIndicadores
  anterior: ResumoIndicadores
  // Mês a mês, na mesma ordem: o 1º mês do atual se compara ao 1º do anterior
  mensal: { atual: MesIndicadores[]; anterior: MesIndicadores[] }
  // Uma linha por classe com faturas no recorte
  por_classe: { classe: ClasseConsumo; receita_faturada: number; receita_faturada_anterior: number }[]
}

export function useIndicadores(filtros: Filtros) {
  const { municipio, classe } = filtros
  const { data: opcoes } = useOpcoesFiltros()
  // Os escolhidos ou o último ano da base contra o anterior. O período mostrado é o
  // comparado; o base é a comparação ("período anterior" na API)
  const periodos = opcoes ? periodosComparados(opcoes.competencias, filtros, 'ano-anterior') : undefined

  return useQuery({
    queryKey: ['indicadores', periodos?.base.de, periodos?.base.ate, periodos?.comparado.de, municipio ?? null, classe ?? null],
    queryFn: ({ signal }) => {
      const { base, comparado } = periodos!
      const params = new URLSearchParams({
        inicio: comparado.de,
        fim: comparado.ate,
        inicio_anterior: base.de,
        fim_anterior: base.ate,
      })
      if (municipio) {
        params.set('municipio', municipio)
      }
      if (classe) {
        params.set('classe', classe)
      }
      return apiFetch<IndicadoresGerais>(`/metrics/general?${params}`, { signal })
    },
    enabled: periodos !== undefined,
    // Ao trocar um filtro, os números anteriores ficam esmaecidos até os novos chegarem
    placeholderData: keepPreviousData,
  })
}
