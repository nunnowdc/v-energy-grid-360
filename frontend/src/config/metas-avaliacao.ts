import type { ExecucaoAvaliacao } from '@/hooks/use-avaliacoes-agente'

// Metas do REQ-AI-08, as mesmas de ai-agent/src/avaliacao/golden_set.py
export type MetaAvaliacao = {
  chave: 'taxa_execucao' | 'taxa_component_match' | 'taxa_abstencao' | 'tokens_medio'
  titulo: string
  // O que a métrica mede, em uma frase
  explicacao: string
  meta: number
  // "minimo": atinge com o valor igual ou acima da meta; "maximo": abaixo da meta
  sentido: 'minimo' | 'maximo'
  // Texto da meta, ex.: "90% ou mais"
  textoMeta: string
}

export const metasAvaliacao: MetaAvaliacao[] = [
  {
    chave: 'taxa_execucao',
    titulo: 'Execução das consultas',
    explicacao: 'Perguntas de dados em que a consulta gerada rodou no banco',
    meta: 90,
    sentido: 'minimo',
    textoMeta: '90% ou mais',
  },
  {
    chave: 'taxa_component_match',
    titulo: 'Tabelas certas',
    explicacao: 'Perguntas de dados cuja consulta usou as tabelas esperadas (lidas pela árvore do SQL)',
    meta: 85,
    sentido: 'minimo',
    textoMeta: '85% ou mais',
  },
  {
    chave: 'taxa_abstencao',
    titulo: 'Recusas corretas',
    explicacao: 'Perguntas fora do escopo ou maliciosas que o agente recusou',
    meta: 100,
    sentido: 'minimo',
    textoMeta: '100%',
  },
  {
    chave: 'tokens_medio',
    titulo: 'Tokens por pergunta',
    explicacao: 'Média de tokens gastos em cada pergunta do golden set',
    meta: 1800,
    sentido: 'maximo',
    textoMeta: 'menos de 1.800',
  },
]

// Nulo quando a execução não tem caso daquele tipo
export function atingiuMeta(meta: MetaAvaliacao, execucao: ExecucaoAvaliacao): boolean | null {
  const valor = execucao[meta.chave]
  if (valor === null) {
    return null
  }
  return meta.sentido === 'minimo' ? valor >= meta.meta : valor < meta.meta
}
