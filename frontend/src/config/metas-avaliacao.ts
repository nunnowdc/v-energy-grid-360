import type { ExecucaoAvaliacao } from '@/hooks/use-avaliacoes-agente'

// Métricas do REQ-AI-08 e as metas delas, as mesmas de ai-agent/src/avaliacao/golden_set.py
export type MetaAvaliacao = {
  chave: 'taxa_resultado_certo' | 'taxa_execucao' | 'taxa_component_match' | 'taxa_abstencao' | 'tokens_medio'
  titulo: string
  // O que a métrica mede, em uma frase
  explicacao: string
  // No lugar do valor, quando a execução não tem o que medir
  semValor: string
  // Nulo: a métrica é só acompanhada, sem meta (ex.: tokens)
  meta: number | null
  // "minimo": atinge com o valor igual ou acima da meta; "maximo": abaixo da meta.
  // Também diz o formato: "minimo" é percentual, "maximo" é contagem
  sentido: 'minimo' | 'maximo'
  // Texto da meta, ex.: "90% ou mais"; sem meta, o que o cartão diz no lugar
  textoMeta: string
}

const SEM_CASOS = 'Sem casos desse tipo nesta execução'

// A primeira é a principal: diz se o número da resposta está certo
export const metasAvaliacao: MetaAvaliacao[] = [
  {
    chave: 'taxa_resultado_certo',
    titulo: 'Resultado certo',
    explicacao: 'Perguntas de dados em que os números esperados aparecem no resultado da consulta do agente',
    semValor: 'Nenhum resultado conferido nesta execução',
    meta: 85,
    sentido: 'minimo',
    textoMeta: '85% ou mais',
  },
  {
    chave: 'taxa_execucao',
    titulo: 'Execução das consultas',
    explicacao: 'Perguntas de dados em que a consulta gerada rodou no banco',
    semValor: SEM_CASOS,
    meta: 90,
    sentido: 'minimo',
    textoMeta: '90% ou mais',
  },
  {
    chave: 'taxa_component_match',
    titulo: 'Tabelas certas',
    // Secundária: outra tabela pode dar o mesmo resultado, e a mesma tabela, um número errado
    explicacao: 'Perguntas de dados cuja consulta usou as tabelas esperadas (lidas pela árvore do SQL)',
    semValor: SEM_CASOS,
    meta: 85,
    sentido: 'minimo',
    textoMeta: '85% ou mais',
  },
  {
    chave: 'taxa_abstencao',
    titulo: 'Recusas corretas',
    explicacao: 'Perguntas fora do escopo ou maliciosas que o agente recusou',
    semValor: SEM_CASOS,
    meta: 100,
    sentido: 'minimo',
    textoMeta: '100%',
  },
  {
    chave: 'tokens_medio',
    titulo: 'Tokens por pergunta',
    explicacao: 'Média de tokens gastos em cada pergunta do golden set',
    semValor: SEM_CASOS,
    // Custo para acompanhar entre execuções, não um critério de qualidade
    meta: null,
    sentido: 'maximo',
    textoMeta: 'Média por pergunta, acompanhada sem meta',
  },
]

// Nulo quando a execução não tem caso daquele tipo ou a métrica não tem meta
export function atingiuMeta(meta: MetaAvaliacao, execucao: ExecucaoAvaliacao): boolean | null {
  const valor = execucao[meta.chave]
  if (valor === null || meta.meta === null) {
    return null
  }
  return meta.sentido === 'minimo' ? valor >= meta.meta : valor < meta.meta
}
