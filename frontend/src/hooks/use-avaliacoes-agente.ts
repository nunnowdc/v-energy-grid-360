import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api/api-fetch'

// Formato de GET /api/ai/evaluations, igual ao backend/app/schemas/agent_evaluations.py.
// Cada execução é uma rodada do golden set no agente de verdade, gravada pelo script
// ai-agent/scripts/avaliar_golden_set.py. Só o ADMIN_TI acessa

export type ExecucaoAvaliacao = {
  id: string
  // Instante com fuso, ex.: "2026-11-01T22:10:00Z"
  executada_em: string
  modelo: string | null
  total_casos: number
  casos_aprovados: number
  // Percentuais de 0 a 100; nulos quando a execução não tem caso daquele tipo
  taxa_execucao: number | null
  taxa_component_match: number | null
  taxa_abstencao: number | null
  tokens_medio: number | null
  duracao_ms: number
}

// O que o caso espera do agente: consulta aos dados, documentos ou recusa
export type TipoCaso = 'sql' | 'rag' | 'recusa'

export type CasoAvaliacao = {
  // Id do golden set, ex.: "TC-001"
  caso_id: string
  tipo: TipoCaso
  pergunta: string
  selo: string
  passou: boolean
  // Por que passou ou falhou, em uma frase
  motivo: string
  sql_gerado: string | null
  tokens: number
  tempo_ms: number
}

export type AvaliacoesAgente = {
  // As 30 mais recentes, da mais antiga para a mais nova; vazia antes da primeira
  execucoes: ExecucaoAvaliacao[]
  // Os casos da última execução, na ordem do golden set
  casos: CasoAvaliacao[]
}

export function useAvaliacoesAgente() {
  return useQuery({
    queryKey: ['agente-ia', 'avaliacoes'],
    queryFn: ({ signal }) => apiFetch<AvaliacoesAgente>('/ai/evaluations', { signal }),
  })
}
