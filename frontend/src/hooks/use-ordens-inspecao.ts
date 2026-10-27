import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api/api-fetch'

// Ordens de inspeção ficam numa tabela do backend (não estão na Gold). Rotas propostas:
//   GET    /api/inspections/orders          → { itens: OrdemInspecao[] } (mais recentes primeiro)
//   POST   /api/inspections/order           { ids_uc: string[] } → { ordens: OrdemInspecao[] }
//   PATCH  /api/inspections/{id_ordem}      { status, resultado? } → OrdemInspecao
//   DELETE /api/inspections/{id_ordem}      → OrdemInspecao com status CANCELADA (o registro fica)

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
  // yyyy-MM-ddTHH:mm:ss
  criada_em: string
}

export type MudancaOrdem =
  | { status: 'EM_CAMPO' }
  | { status: 'CONCLUIDA'; resultado: ResultadoInspecao }

const CHAVE_ORDENS = ['ordens-inspecao']

export function useOrdensInspecao() {
  return useQuery({
    queryKey: CHAVE_ORDENS,
    queryFn: ({ signal }) => apiFetch<{ itens: OrdemInspecao[] }>('/inspections/orders', { signal }),
  })
}

// Toda mudança numa ordem também muda a fila (coluna "Ordem")
function useAtualizarDepois() {
  const queryClient = useQueryClient()
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: CHAVE_ORDENS }),
      queryClient.invalidateQueries({ queryKey: ['fila-inspecao'] }),
    ])
}

export function useGerarOrdens() {
  const atualizar = useAtualizarDepois()
  return useMutation({
    mutationFn: (idsUc: string[]) =>
      apiFetch<{ ordens: OrdemInspecao[] }>('/inspections/order', { method: 'POST', corpo: { ids_uc: idsUc } }),
    onSuccess: atualizar,
  })
}

export function useMudarOrdem() {
  const atualizar = useAtualizarDepois()
  return useMutation({
    mutationFn: ({ idOrdem, mudanca }: { idOrdem: string; mudanca: MudancaOrdem }) =>
      apiFetch<OrdemInspecao>(`/inspections/${idOrdem}`, { method: 'PATCH', corpo: mudanca }),
    onSuccess: atualizar,
  })
}

export function useCancelarOrdem() {
  const atualizar = useAtualizarDepois()
  return useMutation({
    mutationFn: (idOrdem: string) => apiFetch<OrdemInspecao>(`/inspections/${idOrdem}`, { method: 'DELETE' }),
    onSuccess: atualizar,
  })
}
