import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useOpcoesFiltros } from '@/hooks/use-opcoes-filtros'
import { apiFetch } from '@/lib/api/api-fetch'
import { anosDaReceita, type Filtros } from '@/lib/filtros-url'

// Formato de GET /api/metrics/revenue-variance?inicio_p0=&inicio_p1=&municipio=&bairro=&classe=,
// igual ao backend/app/schemas/metrics.py. P0 e P1 têm 12 meses cada, a partir de inicio_p0 e
// inicio_p1; sem eles, o backend usa o primeiro ano da base e os últimos 12 meses. A conta é a
// da Gold (agg_receita_preco_volume), feita sobre agg_receita_mensal para qualquer par de anos.
// Os valores de um recorte são a SOMA das células da Gold; os preços são receita ÷ kWh

type Medidas<Valor> = {
  receita_p0: Valor
  receita_p1: Valor
  kwh_p0: Valor
  kwh_p1: Valor
  ucs_p0: Valor
  ucs_p1: Valor
  // Nulo também quando não há consumo no período
  preco_p0: number | null
  preco_p1: number | null
  // Fórmula da Gold: efeito_volume = Δkwh × preco_p0; efeito_preco = Δpreço × kwh_p1.
  // Os dois somados dão receita_p1 − receita_p0
  efeito_volume: Valor
  efeito_preco: Valor
}

// Como chega da API: tudo nulo quando o recorte não tem nenhuma linha na Gold
// (ex.: bairro sem UC industrial, ou o grupo "com geração própria" de um bairro sem GD)
export type DecomposicaoReceita = Medidas<number | null>

// Recorte com dados: só esta vai para os gráficos e tabelas
export type DecomposicaoCompleta = Medidas<number>

export function temDados(medidas: DecomposicaoReceita): medidas is DecomposicaoCompleta {
  const { receita_p0, receita_p1, kwh_p0, kwh_p1, ucs_p0, ucs_p1, efeito_volume, efeito_preco } = medidas
  return [receita_p0, receita_p1, kwh_p0, kwh_p1, ucs_p0, ucs_p1, efeito_volume, efeito_preco].every(
    (valor) => valor !== null,
  )
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

export function useReceita(filtros: Filtros) {
  const { municipio, bairro, classe } = filtros
  const { data: opcoes } = useOpcoesFiltros()
  // Manda sempre os dois anos, para a resposta ser a dos anos que a barra de filtros mostra
  const anos = opcoes ? anosDaReceita(opcoes.competencias, filtros) : undefined

  return useQuery({
    queryKey: ['receita', anos?.base, anos?.comparado, municipio ?? null, bairro ?? null, classe ?? null],
    queryFn: ({ signal }) => {
      const params = new URLSearchParams({ inicio_p0: anos!.base!, inicio_p1: anos!.comparado! })
      if (municipio) {
        params.set('municipio', municipio)
      }
      if (bairro) {
        params.set('bairro', bairro)
      }
      if (classe) {
        params.set('classe', classe)
      }
      return apiFetch<VariacaoReceita>(`/metrics/revenue-variance?${params}`, { signal })
    },
    enabled: anos?.base !== undefined && anos.comparado !== undefined,
    // Ao trocar um filtro, os números anteriores ficam esmaecidos até os novos chegarem
    placeholderData: keepPreviousData,
  })
}
