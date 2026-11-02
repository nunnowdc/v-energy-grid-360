import { keepPreviousData, useQuery } from '@tanstack/react-query'
import type { Perfil } from '@/config/perfis'
import { apiFetch } from '@/lib/api/api-fetch'

// Formato de GET /api/ai/usage?dias=7|30|90, igual ao backend/app/schemas/agent_usage.py.
// Tudo vem da tb_auditoria_agente, que grava cada pergunta feita ao agente no portal.
// A janela termina hoje e os dias são os de Recife. Só o ADMIN_TI acessa

export const janelasDias = [7, 30, 90] as const

export type JanelaDias = (typeof janelasDias)[number]

export type ResumoUsoAgente = {
  perguntas: number
  // Selos certificada e gerada_confiavel
  respondidas_com_dados: number
  // Selo documental_rag
  respondidas_com_documentos: number
  // Selo recusa_honesta
  recusas: number
  // Selo erro_bloqueado
  erros: number
  // Nulos sem nenhuma pergunta no período
  tempo_medio_ms: number | null
  tempo_p95_ms: number | null
  tokens_medio: number | null
  tokens_total: number
  avaliacoes_uteis: number
  avaliacoes_inuteis: number
}

export type DiaUsoAgente = {
  // yyyy-MM-dd
  dia: string
  perguntas: number
  // Com dados ou com documentos
  respondidas: number
  recusas: number
  erros: number
  tempo_medio_ms: number | null
  tokens_medio: number | null
}

export type PerguntaAuditada = {
  // O mesmo id do passo a passo (GET /api/ai/audit/{id})
  id: string
  // Instante com fuso, ex.: "2026-11-01T15:30:00Z"
  data_hora: string
  pergunta: string
  // Nulo nas perguntas de antes do login
  perfil: Perfil | null
  selo: string
  tempo_ms: number
  tokens: number
  // 1 = útil, -1 = não útil, nulo = sem avaliação
  avaliacao: 1 | -1 | null
}

export type UsoAgente = {
  inicio: string
  fim: string
  resumo: ResumoUsoAgente
  // Todos os dias da janela, do mais antigo ao de hoje (com zero nos dias sem perguntas)
  por_dia: DiaUsoAgente[]
  // As 20 mais recentes, da mais nova para a mais antiga
  ultimas: PerguntaAuditada[]
}

export function useUsoAgente(dias: JanelaDias) {
  return useQuery({
    queryKey: ['agente-ia', 'uso', dias],
    queryFn: ({ signal }) => apiFetch<UsoAgente>(`/ai/usage?dias=${dias}`, { signal }),
    // Ao trocar a janela, os números anteriores ficam esmaecidos até os novos chegarem
    placeholderData: keepPreviousData,
  })
}
