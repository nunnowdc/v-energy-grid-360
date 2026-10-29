import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useOpcoesFiltros } from '@/hooks/use-opcoes-filtros'
import { apiFetch } from '@/lib/api/api-fetch'
import { periodoEscolhido, type Filtros } from '@/lib/filtros-url'

// Formato proposto para GET /api/network/continuity?inicio=&fim=&municipio=&alimentador=&causa=
// (ainda não existe no backend). Regras combinadas (docs/backend/impl_filtros.md):
// - DEC e FEC são sempre do alimentador INTEIRO (agg_continuidade_alimentador), nunca do município
// - município só escolhe quais alimentadores entram; causa só filtra as ocorrências
// O período tem de 1 a 24 meses; o anterior tem o mesmo tamanho e termina no mês antes de "inicio"

export type AlimentadorContinuidade = {
  alimentador: string
  municipio_principal: string
  total_ucs: number
  // Menos de 100 UCs: DEC e FEC ficam inflados pelo denominador pequeno
  alimentador_pequeno: boolean
  // Soma dos valores mensais da Gold no período (horas por UC / interrupções por UC)
  dec: number
  fec: number
  dec_sem_dia_critico: number
  dec_anterior: number
}

export type MesContinuidade = {
  mes_referencia: string
  dec: number
  fec: number
}

export type ContinuidadeRede = {
  periodo: { inicio: string; fim: string }
  periodo_anterior: { inicio: string; fim: string }
  // Alimentadores do recorte, do pior DEC para o melhor
  ranking: AlimentadorContinuidade[]
  // Mês a mês do alimentador escolhido ou, sem escolha, do pior do ranking
  serie: { alimentador: string; atual: MesContinuidade[]; anterior: MesContinuidade[] } | null
  // UCs interrompidas (cada ocorrência = 1 UC), dos alimentadores do recorte e da causa escolhida
  ocorrencias: {
    total: number
    total_anterior: number
    por_causa: { causa: string; ocorrencias: number }[]
  }
}

export function useContinuidade(filtros: Filtros) {
  const { municipio, alimentador, causa } = filtros
  const { data: opcoes } = useOpcoesFiltros()
  // O escolhido ou os últimos 12 meses da base, que vêm das opções
  const periodo = opcoes ? periodoEscolhido(opcoes.competencias, filtros) : undefined

  return useQuery({
    queryKey: ['continuidade', periodo?.de, periodo?.ate, municipio ?? null, alimentador ?? null, causa ?? null],
    queryFn: ({ signal }) => {
      const params = new URLSearchParams({ inicio: periodo!.de, fim: periodo!.ate })
      if (municipio) {
        params.set('municipio', municipio)
      }
      if (alimentador) {
        params.set('alimentador', alimentador)
      }
      if (causa) {
        params.set('causa', causa)
      }
      return apiFetch<ContinuidadeRede>(`/network/continuity?${params}`, { signal })
    },
    enabled: periodo !== undefined,
    // Ao trocar um filtro, os números anteriores ficam esmaecidos até os novos chegarem
    placeholderData: keepPreviousData,
  })
}
