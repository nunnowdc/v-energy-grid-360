import { screen, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { AvaliacoesAgente, ExecucaoAvaliacao } from '@/hooks/use-avaliacoes-agente'
import AvaliacaoAgentePage from '@/pages/AvaliacaoAgente/AvaliacaoAgentePage'
import { renderizar } from '@/test/renderizar'

// Avaliações inventadas, no formato de GET /api/ai/evaluations
const execucao = (valores: Partial<ExecucaoAvaliacao> = {}): ExecucaoAvaliacao => ({
  id: 'e1',
  executada_em: '2026-11-01T18:00:00Z',
  modelo: 'modelo-de-teste',
  total_casos: 12,
  casos_aprovados: 7,
  taxa_execucao: 83.3,
  taxa_component_match: 50,
  taxa_abstencao: 100,
  tokens_medio: 7480.6,
  duracao_ms: 186_000,
  ...valores,
})

const avaliacoes: AvaliacoesAgente = {
  execucoes: [execucao(), execucao({ id: 'e2', executada_em: '2026-11-02T01:10:00Z', casos_aprovados: 9, taxa_execucao: 100 })],
  casos: [
    {
      caso_id: 'TC-001',
      tipo: 'sql',
      pergunta: 'Qual o faturamento total da classe comercial em Olinda no ano de 2023?',
      selo: 'gerada_confiavel',
      passou: false,
      motivo: 'Rodou, mas sem a tabela esperada: fact_faturamento',
      sql_gerado: 'SELECT SUM(receita_faturada) FROM agg_receita_mensal',
      tokens: 9_120,
      tempo_ms: 15_400,
    },
    {
      caso_id: 'TC-012',
      tipo: 'recusa',
      pergunta: 'Quem ganhou o jogo de futebol ontem entre Sport e Santa Cruz?',
      selo: 'recusa_honesta',
      passou: true,
      motivo: 'Recusou, como esperado',
      sql_gerado: null,
      tokens: 2_100,
      tempo_ms: 3_000,
    },
  ],
}

function backend(status: number, corpo: unknown) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(
    async () => new Response(JSON.stringify(corpo), { status, headers: { 'Content-Type': 'application/json' } }),
  )
}

// Pelo título do cartão (o mesmo texto pode aparecer nos gráficos)
const cartao = (titulo: string) =>
  screen
    .getAllByText(titulo)
    .find((elemento) => elemento.closest('[data-slot="card-description"]'))!
    .closest('[data-slot="card"]') as HTMLElement

const abrir = () => renderizar(<AvaliacaoAgentePage />, { url: '/avaliacao-agente' })

afterEach(() => {
  vi.restoreAllMocks()
})

test('mostra a última execução com cada métrica comparada à meta', async () => {
  const fetch = backend(200, avaliacoes)
  abrir()

  // 01:10 em UTC é 22:10 do dia anterior em Recife
  expect(await screen.findByText('01/11/2026 22:10')).toBeInTheDocument()
  expect(fetch.mock.calls[0][0]).toBe('/api/ai/evaluations')
  expect(screen.getByText('modelo-de-teste')).toBeInTheDocument()
  expect(screen.getByText(/em 3,1 min/)).toBeInTheDocument()

  expect(within(cartao('Casos aprovados')).getByText('9 de 12')).toBeInTheDocument()
  expect(within(cartao('Casos aprovados')).getByText('75% do golden set')).toBeInTheDocument()
  expect(within(cartao('Execução das consultas')).getByText('100%')).toBeInTheDocument()
  expect(within(cartao('Execução das consultas')).getByText('Meta: 90% ou mais · atingida')).toBeInTheDocument()
  expect(within(cartao('Tabelas certas')).getByText('50%')).toBeInTheDocument()
  expect(within(cartao('Tabelas certas')).getByText('Meta: 85% ou mais · não atingida')).toBeInTheDocument()
  expect(within(cartao('Recusas corretas')).getByText('Meta: 100% · atingida')).toBeInTheDocument()
  // Tokens: a meta é ficar abaixo
  expect(within(cartao('Tokens por pergunta')).getByText('7.481')).toBeInTheDocument()
  expect(within(cartao('Tokens por pergunta')).getByText('Meta: menos de 1.800 · não atingida')).toBeInTheDocument()
})

test('a métrica sem casos daquele tipo fica sem valor, sem dizer que errou a meta', async () => {
  backend(200, { ...avaliacoes, execucoes: [execucao({ taxa_abstencao: null })] })
  abrir()

  await screen.findByText('7 de 12')
  expect(within(cartao('Recusas corretas')).getByText('—')).toBeInTheDocument()
  expect(within(cartao('Recusas corretas')).getByText('Sem casos desse tipo nesta execução')).toBeInTheDocument()
})

test('lista os casos da última execução com o resultado e o motivo', async () => {
  backend(200, avaliacoes)
  abrir()

  const tabela = await screen.findByRole('table')
  const [, primeiro, segundo] = within(tabela).getAllByRole('row')

  expect(within(primeiro).getByText('TC-001')).toBeInTheDocument()
  expect(within(primeiro).getByText('Consulta aos dados')).toBeInTheDocument()
  expect(within(primeiro).getByText('Falhou')).toBeInTheDocument()
  expect(within(primeiro).getByText('Rodou, mas sem a tabela esperada: fact_faturamento')).toHaveAttribute(
    'title',
    'SELECT SUM(receita_faturada) FROM agg_receita_mensal',
  )
  expect(within(primeiro).getByText('Consulta gerada e validada')).toBeInTheDocument()
  expect(within(primeiro).getByText('9.120')).toBeInTheDocument()
  expect(within(primeiro).getByText('15,4 s')).toBeInTheDocument()

  expect(within(segundo).getByText('Recusa')).toBeInTheDocument()
  expect(within(segundo).getByText('Passou')).toBeInTheDocument()
  expect(within(segundo).getByText('Recusou, como esperado')).toBeInTheDocument()
})

test('antes da primeira execução, explica como rodar a avaliação', async () => {
  backend(200, { execucoes: [], casos: [] })
  abrir()

  expect(await screen.findAllByText('Nenhuma avaliação gravada ainda.')).toHaveLength(3)
  expect(screen.getAllByText('python -m scripts.avaliar_golden_set').length).toBeGreaterThan(1)
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
})

test('avaliações indisponíveis mostram a mensagem do backend em cada bloco', async () => {
  backend(503, { detail: 'Avaliações do agente indisponíveis' })
  abrir()

  expect(await screen.findAllByText('Avaliações do agente indisponíveis')).toHaveLength(3)
})
