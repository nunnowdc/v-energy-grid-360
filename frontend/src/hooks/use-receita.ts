import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api/api-fetch'
import type { Filtros } from '@/lib/filtros-url'

// Formato proposto para GET /api/metrics/revenue-variance?municipio=&bairro=&classe=
// (ainda não existe no backend). Vem de agg_receita_preco_volume, com os períodos
// fixos da Gold (P0 = primeiro ano, P1 = últimos 12 meses), sem parâmetro de período.
// Os valores de um recorte são a SOMA das linhas da Gold; os preços são receita ÷ kWh

export type DecomposicaoReceita = {
  receita_p0: number
  receita_p1: number
  kwh_p0: number
  kwh_p1: number
  ucs_p0: number
  ucs_p1: number
  // Nulo quando não há consumo no período
  preco_p0: number | null
  preco_p1: number | null
  // Fórmula da Gold: efeito_volume = Δkwh × preco_p0; efeito_preco = Δpreço × kwh_p1.
  // Os dois somados dão receita_p1 − receita_p0
  efeito_volume: number
  efeito_preco: number
}

// Próximo nível abaixo do filtro: sem município → municípios; com município →
// bairros; com bairro → classes
export type NivelDetalhe = 'municipio' | 'bairro' | 'classe'

export type VariacaoReceita = {
  periodo_p0: { inicio: string; fim: string }
  periodo_p1: { inicio: string; fim: string }
  total: DecomposicaoReceita
  // UCs com e sem geração própria (painel solar)
  por_gd: ({ possui_gd: boolean } & DecomposicaoReceita)[]
  detalhamento: {
    nivel: NivelDetalhe
    // "nome" é o município, o bairro ou o código da classe
    linhas: ({ nome: string } & DecomposicaoReceita)[]
  }
}

export function useReceita({ municipio, bairro, classe }: Filtros) {
  return useQuery({
    queryKey: ['receita', municipio ?? null, bairro ?? null, classe ?? null],
    queryFn: ({ signal }) => {
      const params = new URLSearchParams()
      if (municipio) {
        params.set('municipio', municipio)
      }
      if (bairro) {
        params.set('bairro', bairro)
      }
      if (classe) {
        params.set('classe', classe)
      }
      const consulta = params.size > 0 ? `?${params}` : ''
      return apiFetch<VariacaoReceita>(`/metrics/revenue-variance${consulta}`, { signal })
    },
    // Ao trocar um filtro, os números anteriores ficam esmaecidos até os novos chegarem
    placeholderData: keepPreviousData,
  })
}
