import { keepPreviousData, useQuery } from '@tanstack/react-query'
import type { ClasseConsumo } from '@/config/classes'
import { useOpcoesFiltros } from '@/hooks/use-opcoes-filtros'
import { apiFetch } from '@/lib/api/api-fetch'
import { janelaDoPeriodo, type Filtros } from '@/lib/filtros-url'

// Formato de GET /api/metrics/general?inicio=yyyy-MM&fim=yyyy-MM&municipio=&classe=, igual ao
// backend/app/schemas/metrics.py. Tudo vem de agg_receita_mensal, somado no recorte pedido.
// O período tem 3, 6 ou 12 meses; o anterior tem o mesmo tamanho e termina no mês antes de "inicio"

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

export function useIndicadores({ meses, ate, municipio, classe }: Filtros) {
  const { data: opcoes } = useOpcoesFiltros()
  // O período termina no mês escolhido ou no último mês da base, que vem das opções
  const janela = opcoes ? janelaDoPeriodo(opcoes.competencias, meses, ate) : undefined

  return useQuery({
    queryKey: ['indicadores', janela?.inicio, janela?.fim, municipio ?? null, classe ?? null],
    queryFn: ({ signal }) => {
      const params = new URLSearchParams({ inicio: janela!.inicio, fim: janela!.fim! })
      if (municipio) {
        params.set('municipio', municipio)
      }
      if (classe) {
        params.set('classe', classe)
      }
      return apiFetch<IndicadoresGerais>(`/metrics/general?${params}`, { signal })
    },
    enabled: janela?.inicio !== undefined,
    // Ao trocar um filtro, os números anteriores ficam esmaecidos até os novos chegarem
    placeholderData: keepPreviousData,
  })
}
