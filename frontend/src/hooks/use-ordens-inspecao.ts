import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api/api-fetch'
import { ErroApi } from '@/lib/api/erro-api'
import type { Filtros } from '@/lib/filtros-url'

// Ordens de inspeção ficam na tabela ordens_inspecao do backend (não estão na Gold):
//   GET    /api/inspections/orders?municipio=&bairro=&classe= → { itens: OrdemInspecao[] } (mais recentes primeiro)
//   POST   /api/inspections/order           { ids_uc: string[] } → { ordens: OrdemInspecao[] }
//   PATCH  /api/inspections/{id_ordem}      { status, resultado? } → OrdemInspecao
//   DELETE /api/inspections/{id_ordem}      → OrdemInspecao com status CANCELADA (o registro fica)
// Gerar é tudo ou nada: se uma UC do lote já tem ordem aberta, nenhuma é criada (409)

export type StatusOrdem = 'ABERTA' | 'EM_CAMPO' | 'CONCLUIDA' | 'CANCELADA'

// Mesmos valores de fact_inspecoes.resultado
export type ResultadoInspecao = 'IRREGULARIDADE_CONFIRMADA' | 'SEM_IRREGULARIDADE'

export type OrdemInspecao = {
  id_ordem: string
  id_uc: string
  municipio: string
  bairro: string
  status: StatusOrdem
  // Só existe na ordem concluída
  resultado: ResultadoInspecao | null
  // Instante em UTC: "2026-10-28T21:09:39.757316Z"
  criada_em: string
  // Quem gerou e quem mudou por último. Ordens de antes da autoria vêm sem nome (null)
  criada_por_nome: string | null
  atualizada_por_nome: string | null
}

export type MudancaOrdem =
  | { status: 'EM_CAMPO' }
  | { status: 'CONCLUIDA'; resultado: ResultadoInspecao }

const CHAVE_ORDENS = ['ordens-inspecao']

export function useOrdensInspecao({ municipio, bairro, classe }: Filtros) {
  return useQuery({
    queryKey: [...CHAVE_ORDENS, municipio ?? null, bairro ?? null, classe ?? null],
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
      const busca = params.toString()
      return apiFetch<{ itens: OrdemInspecao[] }>(`/inspections/orders${busca ? `?${busca}` : ''}`, { signal })
    },
    // Ao contrário da Gold, as ordens mudam a qualquer hora (outra pessoa da equipe
    // gera ou conclui): busca de novo sempre que a tela abre
    staleTime: 0,
  })
}

// Toda mudança numa ordem também muda a fila (coluna "Ordem"). No 404 e no 409,
// alguém mexeu na ordem antes: recarrega para a tela mostrar a situação atual
function useAtualizarDepois() {
  const queryClient = useQueryClient()
  const atualizar = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: CHAVE_ORDENS }),
      queryClient.invalidateQueries({ queryKey: ['fila-inspecao'] }),
    ])
  return {
    onSuccess: atualizar,
    onError: (erro: Error) => {
      if (erro instanceof ErroApi && (erro.status === 404 || erro.status === 409)) {
        return atualizar()
      }
    },
  }
}

export function useGerarOrdens() {
  const atualizarDepois = useAtualizarDepois()
  return useMutation({
    mutationFn: (idsUc: string[]) =>
      apiFetch<{ ordens: OrdemInspecao[] }>('/inspections/order', { method: 'POST', corpo: { ids_uc: idsUc } }),
    ...atualizarDepois,
  })
}

export function useMudarOrdem() {
  const atualizarDepois = useAtualizarDepois()
  return useMutation({
    mutationFn: ({ idOrdem, mudanca }: { idOrdem: string; mudanca: MudancaOrdem }) =>
      apiFetch<OrdemInspecao>(`/inspections/${idOrdem}`, { method: 'PATCH', corpo: mudanca }),
    ...atualizarDepois,
  })
}

export function useCancelarOrdem() {
  const atualizarDepois = useAtualizarDepois()
  return useMutation({
    mutationFn: (idOrdem: string) => apiFetch<OrdemInspecao>(`/inspections/${idOrdem}`, { method: 'DELETE' }),
    ...atualizarDepois,
  })
}
