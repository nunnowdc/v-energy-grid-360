import { keepPreviousData, useQuery } from '@tanstack/react-query'
import type { ClasseConsumo } from '@/config/classes'
import type { StatusOrdem } from '@/hooks/use-ordens-inspecao'
import { apiFetch } from '@/lib/api/api-fetch'
import type { Filtros } from '@/lib/filtros-url'

// GET /api/inspections/queue?municipio=&bairro=&classe=&pagina=&limite= (limite até 50; bairro
// só com município). Vem de fila_inspecao, na prioridade já calculada pela Gold.
// Sem nome e endereço do titular: para a fila bastam o ID e o bairro (LGPD)

export type ItemFila = {
  prioridade: number
  id_uc: string
  // 0 a 100 (v1 por regras, pesos ainda em calibração)
  score: number
  // Regras que dispararam, como vêm da Gold: "Queda de consumo >= 50% (+40); Medidor eletromecanico (+15)"
  motivo_suspeita: string
  kwh_recuperavel_estimado_ano: number
  municipio: string
  bairro: string
  classe: ClasseConsumo
  // Ordem do portal ainda não encerrada para esta UC (tabela do backend, não da Gold)
  ordem_aberta: { id_ordem: string; status: StatusOrdem } | null
}

export type FilaInspecao = {
  // Última competência usada no cálculo da fila (yyyy-MM-dd)
  data_referencia: string
  // Totais da fila inteira no recorte, não só da página
  resumo: { ucs: number; kwh_recuperavel_estimado_ano: number }
  pagina: number
  limite: number
  total: number
  itens: ItemFila[]
}

export const LIMITE_FILA = 20

export function useFilaInspecao({ municipio, bairro, classe }: Filtros, pagina: number) {
  return useQuery({
    queryKey: ['fila-inspecao', municipio ?? null, bairro ?? null, classe ?? null, pagina],
    queryFn: ({ signal }) => {
      const params = new URLSearchParams({ pagina: String(pagina), limite: String(LIMITE_FILA) })
      if (municipio) {
        params.set('municipio', municipio)
      }
      if (bairro) {
        params.set('bairro', bairro)
      }
      if (classe) {
        params.set('classe', classe)
      }
      return apiFetch<FilaInspecao>(`/inspections/queue?${params}`, { signal })
    },
    // Ao trocar de página ou de filtro, a tabela anterior fica esmaecida até a nova chegar
    placeholderData: keepPreviousData,
    // A coluna "Ordem" muda quando alguém gera ou conclui uma ordem: busca de novo ao abrir a tela
    staleTime: 0,
  })
}
