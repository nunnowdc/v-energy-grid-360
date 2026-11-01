import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useOpcoesFiltros } from '@/hooks/use-opcoes-filtros'
import { apiFetch } from '@/lib/api/api-fetch'
import { periodosComparados, type Filtros } from '@/lib/filtros-url'

// Resposta de GET /api/network/continuity?inicio=&fim=&inicio_anterior=&fim_anterior=&municipio=&alimentador=&causa=
// (backend/app/schemas/network.py). Regras combinadas (docs/backend/impl_filtros.md):
// - DEC e FEC são sempre do alimentador INTEIRO (agg_continuidade_alimentador), nunca do município
// - município só escolhe quais alimentadores entram; causa só filtra as ocorrências
// Os dois períodos têm o mesmo tamanho (1 a 24 meses) e o anterior termina antes de "inicio";
// sem inicio_anterior e fim_anterior, vale o imediatamente anterior (como em /metrics/general)

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

// Alimentador dos destaques da tela (card "Pior DEC" e gráfico mês a mês): o pior DEC entre os
// com 100 UCs ou mais, porque nos pequenos poucas interrupções já inflam o DEC. Se todos forem
// pequenos (ou se só houver o alimentador escolhido), vale o primeiro do ranking
export function alimentadorEmDestaque(ranking: AlimentadorContinuidade[]) {
  return ranking.find((linha) => !linha.alimentador_pequeno) ?? ranking[0]
}

// habilitada: false deixa a consulta parada (ex.: a do gráfico, quando a série já veio na principal)
export function useContinuidade(filtros: Filtros, habilitada = true) {
  const { municipio, alimentador, causa } = filtros
  const { data: opcoes } = useOpcoesFiltros()
  // Os escolhidos ou o último ano da base contra o anterior
  const periodos = opcoes ? periodosComparados(opcoes.competencias, filtros, 'ano-anterior') : undefined

  return useQuery({
    queryKey: [
      'continuidade',
      periodos?.base.de,
      periodos?.base.ate,
      periodos?.comparado.de,
      municipio ?? null,
      alimentador ?? null,
      causa ?? null,
    ],
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
      if (alimentador) {
        params.set('alimentador', alimentador)
      }
      if (causa) {
        params.set('causa', causa)
      }
      return apiFetch<ContinuidadeRede>(`/network/continuity?${params}`, { signal })
    },
    enabled: habilitada && periodos !== undefined,
    // Ao trocar um filtro, os números anteriores ficam esmaecidos até os novos chegarem
    placeholderData: keepPreviousData,
  })
}
