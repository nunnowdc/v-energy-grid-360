import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { AuditoriaAgente } from '@/hooks/use-agente-ia'
import type { DiaUsoAgente, UsoAgente } from '@/hooks/use-uso-agente'
import AgenteIaPage from '@/pages/AgenteIa/AgenteIaPage'
import { renderizar } from '@/test/renderizar'

// Uso inventado, no formato de GET /api/ai/usage
const dia = (data: string, valores: Partial<DiaUsoAgente> = {}): DiaUsoAgente => ({
  dia: data,
  perguntas: 0,
  respondidas: 0,
  recusas: 0,
  erros: 0,
  tempo_medio_ms: null,
  tokens_medio: null,
  ...valores,
})

const uso = (valores: Partial<UsoAgente> = {}): UsoAgente => ({
  inicio: '2026-10-03',
  fim: '2026-11-01',
  resumo: {
    perguntas: 97,
    respondidas_com_dados: 69,
    respondidas_com_documentos: 5,
    recusas: 23,
    erros: 0,
    tempo_medio_ms: 19_253,
    tempo_p95_ms: 42_910.5,
    tokens_medio: 8048.1,
    tokens_total: 780_664,
    avaliacoes_uteis: 5,
    avaliacoes_inuteis: 1,
  },
  por_dia: [
    dia('2026-10-31', { perguntas: 1, respondidas: 1, tempo_medio_ms: 4000, tokens_medio: 4852 }),
    dia('2026-11-01', { perguntas: 2, respondidas: 1, recusas: 1, tempo_medio_ms: 9000, tokens_medio: 7231 }),
  ],
  ultimas: [
    {
      id: 'a1',
      data_hora: '2026-11-01T16:16:00Z',
      pergunta: 'me diga algo que eu deveria saber',
      perfil: 'ADMIN_TI',
      selo: 'recusa_honesta',
      tempo_ms: 2_500,
      tokens: 2_240,
      avaliacao: -1,
    },
    {
      id: 'a2',
      data_hora: '2026-10-31T22:13:00Z',
      pergunta: 'Qual o faturamento em Recife no ano de 2024?',
      perfil: null,
      selo: 'certificada',
      tempo_ms: 4_000,
      tokens: 4_852,
      avaliacao: 1,
    },
  ],
  ...valores,
})

const auditoria: AuditoriaAgente = {
  id: 'a2',
  data_hora: '2026-10-31T22:13:00Z',
  pergunta_original: 'Qual o faturamento em Recife no ano de 2024?',
  pergunta_autonoma: 'Qual o faturamento em Recife no ano de 2024?',
  rota_escolhida: 'sql',
  hit_cache: true,
  sql_gerado: "SELECT SUM(receita_faturada) FROM agg_receita_mensal WHERE municipio = 'Recife'",
  linhas_retornadas: 1,
  amostra_resultado_json: '[{"receita_total": 68560067.39}]',
  selo_confianca: 'certificada',
  passos_execucao: JSON.stringify([
    'Nó 1 — Filtro de segurança: aprovado.',
    'Nó 6 — Cache certificado: faturamento_por_municipio_ano (recife, 2024).',
    'Nó 11 — Síntese gerada. Selo: certificada.',
  ]),
  tempo_execucao_ms: 4000,
  tokens_prompt: 4800,
  tokens_resposta: 52,
  erro_mensagem: null,
  feedback_usuario: 1,
}

type Resposta = { status?: number; corpo: unknown }

// Backend falso: o uso de cada janela e a auditoria de cada pergunta
function backend(usoPorJanela: Record<string, Resposta>) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (entrada) => {
    const url = new URL(String(entrada), 'http://portal.test')
    const { status = 200, corpo } =
      url.pathname === '/api/ai/usage'
        ? usoPorJanela[url.searchParams.get('dias') ?? '']
        : url.pathname === `/api/ai/audit/${auditoria.id}`
          ? { corpo: auditoria }
          : { status: 404, corpo: { detail: 'Não encontrado' } }
    return new Response(JSON.stringify(corpo), { status, headers: { 'Content-Type': 'application/json' } })
  })
}

const urlsUso = (fetch: ReturnType<typeof backend>) =>
  fetch.mock.calls.map(([entrada]) => String(entrada)).filter((url) => url.startsWith('/api/ai/usage'))

// Pelo título do cartão: "Sem resposta segura" também é o nome de um selo na tabela
const cartao = (titulo: string) =>
  screen
    .getAllByText(titulo)
    .find((elemento) => elemento.closest('[data-slot="card-description"]'))!
    .closest('[data-slot="card"]') as HTMLElement

afterEach(() => {
  vi.restoreAllMocks()
})

test('mostra o uso dos últimos 30 dias com os números de cada cartão', async () => {
  const fetch = backend({ '30': { corpo: uso() } })
  renderizar(<AgenteIaPage />, { url: '/agente-ia' })

  expect(await screen.findByText('03/10/2026')).toBeInTheDocument()
  expect(urlsUso(fetch)).toEqual(['/api/ai/usage?dias=30'])
  expect(screen.getByRole('button', { name: 'Últimos 30 dias' })).toHaveAttribute('aria-pressed', 'true')

  expect(within(cartao('Perguntas')).getByText('97')).toBeInTheDocument()
  expect(within(cartao('Perguntas')).getByText('Média de 48,5 por dia')).toBeInTheDocument()
  // 69 + 5 de 97
  expect(within(cartao('Respondidas')).getByText('76,3%')).toBeInTheDocument()
  expect(within(cartao('Respondidas')).getByText('69 com dados e 5 com documentos')).toBeInTheDocument()
  expect(within(cartao('Sem resposta segura')).getByText('23,7%')).toBeInTheDocument()
  expect(within(cartao('Sem resposta segura')).getByText('23 recusas e 0 erros')).toBeInTheDocument()
  expect(within(cartao('Tempo médio de resposta')).getByText('19,3 s')).toBeInTheDocument()
  expect(within(cartao('Tempo médio de resposta')).getByText('95% em até 42,9 s')).toBeInTheDocument()
  expect(within(cartao('Tokens por pergunta')).getByText('8.048')).toBeInTheDocument()
  expect(within(cartao('Tokens por pergunta')).getByText(/780,7\smil no período/)).toBeInTheDocument()
  expect(within(cartao('Avaliações')).getByText('6')).toBeInTheDocument()
  expect(within(cartao('Avaliações')).getByText('5 úteis e 1 não úteis')).toBeInTheDocument()
})

test('lista as últimas perguntas com perfil, resultado, tempo e avaliação', async () => {
  backend({ '30': { corpo: uso() } })
  renderizar(<AgenteIaPage />, { url: '/agente-ia' })

  const tabela = await screen.findByRole('table')
  const [, primeira, segunda] = within(tabela).getAllByRole('row')

  expect(within(primeira).getByText('me diga algo que eu deveria saber')).toBeInTheDocument()
  // 16:16 em UTC é 13:16 em Recife
  expect(within(primeira).getByText('01/11/2026 13:16')).toBeInTheDocument()
  expect(within(primeira).getByText('Administrador (TI)')).toBeInTheDocument()
  expect(within(primeira).getByText('Sem resposta segura')).toBeInTheDocument()
  expect(within(primeira).getByText('2,5 s')).toBeInTheDocument()
  expect(within(primeira).getByText('2.240')).toBeInTheDocument()
  expect(within(primeira).getByText('Não útil')).toBeInTheDocument()

  // Pergunta de antes do login: sem perfil
  expect(within(segunda).getByTitle('Pergunta de antes do login')).toHaveTextContent('—')
  expect(within(segunda).getByText('Consulta certificada')).toBeInTheDocument()
  expect(within(segunda).getByText('Útil')).toBeInTheDocument()
})

test('o passo a passo da pergunta abre num painel ao lado', async () => {
  const fetch = backend({ '30': { corpo: uso() } })
  renderizar(<AgenteIaPage />, { url: '/agente-ia' })

  const tabela = await screen.findByRole('table')
  const segunda = within(tabela).getAllByRole('row')[2]
  fireEvent.click(within(segunda).getByRole('button', { name: 'Passo a passo' }))

  const painel = await screen.findByRole('dialog')
  expect(within(painel).getByText('Como o agente chegou na resposta')).toBeInTheDocument()
  expect(within(painel).getByText('Qual o faturamento em Recife no ano de 2024?')).toBeInTheDocument()
  expect(await within(painel).findByText(/agg_receita_mensal/)).toBeInTheDocument()
  expect(fetch.mock.calls.map(([entrada]) => String(entrada))).toContain('/api/ai/audit/a2')
})

test('trocar a janela busca os outros dias e guarda a escolha no endereço', async () => {
  const fetch = backend({
    '30': { corpo: uso() },
    '7': { corpo: uso({ inicio: '2026-10-26', resumo: { ...uso().resumo, perguntas: 3 } }) },
  })
  renderizar(<AgenteIaPage />, { url: '/agente-ia' })
  await screen.findByText('03/10/2026')

  fireEvent.click(screen.getByRole('button', { name: 'Últimos 7 dias' }))

  expect(await screen.findByText('26/10/2026')).toBeInTheDocument()
  expect(urlsUso(fetch)).toEqual(['/api/ai/usage?dias=30', '/api/ai/usage?dias=7'])
  expect(screen.getByRole('button', { name: 'Últimos 7 dias' })).toHaveAttribute('aria-pressed', 'true')
  expect(within(cartao('Perguntas')).getByText('3')).toBeInTheDocument()
})

test.each([
  ['/agente-ia?dias=90', '90'],
  ['/agente-ia?dias=15', '30'],
  ['/agente-ia?dias=abc', '30'],
])('o endereço %s abre com a janela de %s dias', async (url, dias) => {
  const fetch = backend({ [dias]: { corpo: uso() } })
  renderizar(<AgenteIaPage />, { url })

  await waitFor(() => expect(urlsUso(fetch)).toEqual([`/api/ai/usage?dias=${dias}`]))
  expect(screen.getByRole('button', { name: `Últimos ${dias} dias` })).toHaveAttribute('aria-pressed', 'true')
})

test('período sem perguntas avisa em vez de mostrar zeros', async () => {
  const vazio = uso({
    resumo: {
      ...uso().resumo,
      perguntas: 0,
      respondidas_com_dados: 0,
      respondidas_com_documentos: 0,
      recusas: 0,
      tempo_medio_ms: null,
      tempo_p95_ms: null,
      tokens_medio: null,
      tokens_total: 0,
      avaliacoes_uteis: 0,
      avaliacoes_inuteis: 0,
    },
    por_dia: [dia('2026-11-01')],
    ultimas: [],
  })
  backend({ '30': { corpo: vazio } })
  renderizar(<AgenteIaPage />, { url: '/agente-ia' })

  expect(await screen.findAllByText('Nenhuma pergunta ao agente nesse período.')).toHaveLength(4)
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
})

test('auditoria indisponível mostra a mensagem do backend em cada bloco', async () => {
  backend({ '30': { status: 503, corpo: { detail: 'Auditoria do agente indisponível' } } })
  renderizar(<AgenteIaPage />, { url: '/agente-ia' })

  expect(await screen.findAllByText('Auditoria do agente indisponível')).toHaveLength(4)
})
