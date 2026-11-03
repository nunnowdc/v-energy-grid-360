import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api/api-fetch'

// Rota dos insights (ai-agent/src/insights/, montada no backend em /api/ai):
//   GET /api/ai/insights/{tela}/{entidade_id} → InsightIa
// visao_360_uc: um insight por UC (entidade = ID da UC). É a única tela com insight
// (decisão do time, veja "Suposições e decisões do time" no README da raiz)
export type TelaInsight = 'visao_360_uc'

// auditado_llm: cada número do texto foi conferido com os dados consultados.
// template_fallback: a conferência falhou e o texto é um aviso padrão
export type SeloInsight = 'auditado_llm' | 'template_fallback'

export type InsightIa = {
  tela: TelaInsight
  entidade_id: string
  insight_texto: string
  // A linha de dados mais recente usada no texto; as chaves mudam de uma tela para outra
  metricas_destaque: Record<string, unknown>
  // O backend tipa como texto; um selo novo fica sem etiqueta
  selo: SeloInsight | (string & {})
  tempo_ms: number
  // Tabelas de onde vieram os números, como no /ai/ask (pedido ao time de IA; ainda não vem)
  fontes?: string[]
}

// Na primeira vez, a IA escreve o texto na hora; depois ele vem guardado do banco
const TEMPO_LIMITE_INSIGHT_MS = 60_000

export function useInsightIa(tela: TelaInsight, entidadeId: string) {
  return useQuery({
    queryKey: ['insight-ia', tela, entidadeId],
    queryFn: ({ signal }) =>
      apiFetch<InsightIa>(`/ai/insights/${tela}/${encodeURIComponent(entidadeId)}`, {
        signal,
        tempoLimiteMs: TEMPO_LIMITE_INSIGHT_MS,
      }),
    // O texto fica guardado no banco, então não muda enquanto a página está aberta
    staleTime: Infinity,
    // Cada tentativa pode chamar o modelo de novo; quem quiser tenta pelo botão do erro
    retry: false,
  })
}
