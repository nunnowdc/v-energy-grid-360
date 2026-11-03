import { useMutation, useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api/api-fetch'

// Rotas do agente (ai-agent/src/api/ai_router.py, montadas no backend em /api/ai):
//   POST /api/ai/ask              PerguntaAgente → RespostaAgente
//   GET  /api/ai/audit/{audit_id} → AuditoriaAgente (linha de tb_auditoria_agente)
//   POST /api/ai/feedback         { audit_id, feedback: 1 | -1 }

export type SeloConfianca =
  | 'certificada'
  | 'gerada_confiavel'
  | 'documental_rag'
  | 'recusa_honesta'
  | 'erro_bloqueado'

export type TurnoConversa = { role: 'user' | 'assistant'; content: string }

// Sem quem pergunta: o backend usa a conta do cookie de login (e o perfil dela) na auditoria
export type PerguntaAgente = {
  session_id: string
  message: string
  // Tela de onde veio a pergunta e, quando houver, a UC aberta
  context?: { page: string; id_uc?: string }
  // Perguntas e respostas anteriores, para entender "e em 2023?"
  history?: TurnoConversa[]
}

// Tela que mostra os dados da resposta, escolhida pelo agente a partir da consulta
// executada (ai-agent/src/services/tela_dashboard.py). Os valores vêm como estão
// no SQL, ex.: "recife"; o painel confere com as opções dos filtros antes de aplicar
export type DashboardAgente = {
  tela: 'indicadores' | 'receita' | 'continuidade' | 'inspecoes' | 'visao_360'
  filtros: {
    municipio?: string | null
    bairro?: string | null
    classe?: string | null
    alimentador?: string | null
    causa?: string | null
    // Só na visao_360
    id_uc?: string | null
    // Meses consultados (yyyy-MM), ex.: { de: "2024-01", ate: "2024-12" } para "em 2024"
    periodo?: { de: string; ate: string } | null
    // Só quando a consulta compara dois períodos (2023 e 2024): o mais antigo
    periodo_base?: { de: string; ate: string } | null
  }
}

export type RespostaAgente = {
  answer: string
  sql: string | null
  audit_id: string
  // O backend tipa como texto; um selo novo cai no visual padrão
  selo_confianca: SeloConfianca | (string & {})
  fontes: string[]
  tempo_ms: number
  // null: a resposta não tem consulta ou os dados dela não estão em nenhuma tela
  dashboard?: DashboardAgente | null
}

export type AuditoriaAgente = {
  id: string
  // yyyy-MM-ddTHH:mm:ss.ffffffZ
  data_hora: string
  pergunta_original: string
  // A pergunta depois de completada com o histórico
  pergunta_autonoma: string
  rota_escolhida: string
  hit_cache: boolean
  sql_gerado: string | null
  linhas_retornadas: number
  // Texto JSON com até 3 linhas do resultado, campos pessoais mascarados
  amostra_resultado_json: string | null
  selo_confianca: string
  // Texto JSON com a lista de passos ("Nó 4 — Roteador: ...")
  passos_execucao: string | string[]
  tempo_execucao_ms: number
  tokens_prompt: number
  tokens_resposta: number
  erro_mensagem: string | null
  feedback_usuario: number | null
}

// O agente faz várias chamadas ao modelo; com novas tentativas de SQL passa de 30 s
const TEMPO_LIMITE_AGENTE_MS = 90_000

export function usePerguntarAgente() {
  return useMutation({
    mutationFn: (pergunta: PerguntaAgente) =>
      apiFetch<RespostaAgente>('/ai/ask', {
        method: 'POST',
        corpo: pergunta,
        tempoLimiteMs: TEMPO_LIMITE_AGENTE_MS,
      }),
  })
}

// O registro não muda depois de gravado, então não precisa buscar de novo
export function useAuditoriaAgente(auditId: string | undefined) {
  return useQuery({
    queryKey: ['agente-ia', 'auditoria', auditId],
    queryFn: ({ signal }) => apiFetch<AuditoriaAgente>(`/ai/audit/${auditId}`, { signal }),
    enabled: auditId !== undefined,
    staleTime: Infinity,
  })
}

export function useFeedbackAgente() {
  return useMutation({
    mutationFn: ({ auditId, util }: { auditId: string; util: boolean }) =>
      apiFetch<{ status: string }>('/ai/feedback', {
        method: 'POST',
        corpo: { audit_id: auditId, feedback: util ? 1 : -1 },
      }),
  })
}
