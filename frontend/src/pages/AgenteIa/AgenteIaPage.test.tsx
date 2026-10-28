import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { Route, Routes } from 'react-router'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import type { AuditoriaAgente, RespostaAgente } from '@/hooks/use-agente-ia'
import AgenteIaPage from '@/pages/AgenteIa/AgenteIaPage'
import { renderizar } from '@/test/renderizar'

// Respostas e auditorias inventadas, no formato das rotas reais do agente
const resposta = (auditId: string, valores: Partial<RespostaAgente> = {}): RespostaAgente => ({
  answer: `Resposta ${auditId}`,
  sql: 'SELECT 1',
  audit_id: auditId,
  selo_confianca: 'certificada',
  fontes: [],
  tempo_ms: 7400,
  ...valores,
})

const auditoria = (auditId: string, valores: Partial<AuditoriaAgente> = {}): AuditoriaAgente => ({
  id: auditId,
  data_hora: '2026-10-28T01:25:04.952038Z',
  pergunta_original: 'Qual o faturamento em Olinda?',
  pergunta_autonoma: 'Qual o faturamento em Olinda?',
  rota_escolhida: 'sql',
  hit_cache: true,
  sql_gerado: "SELECT SUM(receita_faturada) FROM agg_receita_mensal WHERE municipio = 'Olinda'",
  linhas_retornadas: 1,
  amostra_resultado_json: '[{"municipio": "Olinda", "receita_total": 1500.5}]',
  selo_confianca: 'certificada',
  passos_execucao: JSON.stringify([
    'Nó 1 — Filtro de segurança: aprovado.',
    "Nó 4 — Roteador: 'sql' (confiança 99%). Consulta de faturamento.",
    'Nó 6 — Cache certificado: faturamento_por_municipio_ano (olinda, 2023).',
    'Nó 9 — Execução SQL OK. 1 linha(s) em 121ms.',
    'Nó 11 — Síntese gerada. Selo: certificada.',
  ]),
  tempo_execucao_ms: 7400,
  tokens_prompt: 4000,
  tokens_resposta: 100,
  erro_mensagem: null,
  feedback_usuario: null,
  ...valores,
})

type Resposta = { status?: number; corpo: unknown }

// Backend falso: cada POST /ask consome a próxima resposta da fila
function backend({ perguntas, auditorias }: { perguntas: Resposta[]; auditorias: Record<string, AuditoriaAgente> }) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, init) => {
    const caminho = String(url)
    let saida: Resposta = { status: 404, corpo: { detail: 'Não encontrado' } }
    if (caminho === '/api/ai/ask') {
      saida = perguntas.shift() ?? saida
    } else if (caminho.startsWith('/api/ai/audit/')) {
      const encontrada = auditorias[caminho.split('/').at(-1)!]
      saida = encontrada ? { corpo: encontrada } : saida
    } else if (caminho === '/api/ai/feedback' && init?.method === 'POST') {
      saida = { corpo: { status: 'ok' } }
    }
    return new Response(JSON.stringify(saida.corpo), {
      status: saida.status ?? 200,
      headers: { 'Content-Type': 'application/json' },
    })
  })
}

const corpoDas = (fetch: ReturnType<typeof backend>, caminho: string) =>
  fetch.mock.calls
    .filter(([url]) => String(url) === caminho)
    .map(([, init]) => JSON.parse(String(init!.body)))

function abrir() {
  return renderizar(
    <Routes>
      <Route path="/agente-ia" element={<AgenteIaPage />} />
    </Routes>,
    { url: '/agente-ia' },
  )
}

function perguntar(texto: string) {
  fireEvent.change(screen.getByLabelText('Sua pergunta'), { target: { value: texto } })
  fireEvent.click(screen.getByRole('button', { name: 'Enviar pergunta' }))
}

const passosNoGrafo = () =>
  within(screen.getByRole('list', { name: 'Passos do agente' }))
    .getAllByRole('listitem')
    .filter((item) => item.parentElement?.getAttribute('aria-label') === 'Passos do agente')
    .map((item) => item.querySelector('p')!.textContent)

beforeEach(() => {
  let sequencia = 0
  vi.spyOn(crypto, 'randomUUID').mockImplementation(() => `00000000-0000-4000-8000-00000000000${sequencia++}` as `${string}-${string}-${string}-${string}-${string}`)
})

afterEach(() => {
  vi.restoreAllMocks()
})

test('conversa vazia oferece sugestões e o painel explica o que vai aparecer', () => {
  backend({ perguntas: [], auditorias: {} })
  abrir()
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Agente de IA')
  expect(within(screen.getByRole('list', { name: 'Sugestões de pergunta' })).getAllByRole('button')).toHaveLength(3)
  expect(screen.getByText(/Faça uma pergunta para ver aqui cada passo/)).toBeInTheDocument()
})

test('a sugestão vira pergunta, a resposta chega com selo e o painel mostra o grafo', async () => {
  const fetch = backend({ perguntas: [{ corpo: resposta('a1') }], auditorias: { a1: auditoria('a1') } })
  abrir()

  fireEvent.click(screen.getByRole('button', { name: 'Qual o faturamento em Recife no ano de 2024?' }))
  expect(screen.getByText(/Analisando a pergunta/)).toBeInTheDocument()
  expect(await screen.findByText('Resposta a1')).toBeInTheDocument()

  expect(corpoDas(fetch, '/api/ai/ask')).toEqual([
    {
      user_id: 'teste-admin_ti',
      session_id: '00000000-0000-4000-8000-000000000000',
      message: 'Qual o faturamento em Recife no ano de 2024?',
      context: { page: 'agente_ia' },
      history: [],
    },
  ])
  expect(screen.getByText('Consulta certificada')).toBeInTheDocument()
  expect(screen.getByText('7,4 s')).toBeInTheDocument()

  // O painel abre sozinho na última resposta, com um nó por passo e a auditoria no fim
  await waitFor(() =>
    expect(passosNoGrafo()).toEqual([
      'Nó 1: Filtro de segurança',
      'Nó 4: Roteamento',
      'Nó 6: Consulta certificada',
      'Nó 9: Execução no banco',
      'Nó 11: Resposta final',
      'Nó 12: Auditoria',
    ]),
  )
  // A consulta aparece no nó que a produziu e a amostra no nó da execução
  expect(screen.getByText(/FROM agg_receita_mensal/)).toBeInTheDocument()
  expect(screen.getByRole('cell', { name: '1.500,5' })).toBeInTheDocument()
  expect(screen.getByText('Consulta aos dados')).toBeInTheDocument()
})

test('a pergunta seguinte leva o histórico, e dá para voltar ao passo a passo da anterior', async () => {
  const fetch = backend({
    perguntas: [{ corpo: resposta('a1') }, { corpo: resposta('a2') }],
    auditorias: {
      a1: auditoria('a1'),
      a2: auditoria('a2', { pergunta_original: 'E em 2023?', pergunta_autonoma: 'Qual o faturamento em Olinda em 2023?' }),
    },
  })
  abrir()

  perguntar('Qual o faturamento em Olinda?')
  await screen.findByText('Resposta a1')
  perguntar('E em 2023?')
  await screen.findByText('Resposta a2')

  expect(corpoDas(fetch, '/api/ai/ask')[1].history).toEqual([
    { role: 'user', content: 'Qual o faturamento em Olinda?' },
    { role: 'assistant', content: 'Resposta a1' },
  ])
  expect(await screen.findByText('Qual o faturamento em Olinda em 2023?')).toBeInTheDocument()

  const [verPrimeira] = screen.getAllByRole('button', { name: 'Ver o passo a passo' })
  fireEvent.click(verPrimeira)
  expect(verPrimeira).toHaveAttribute('aria-pressed', 'true')
  await waitFor(() => expect(screen.queryByText('Qual o faturamento em Olinda em 2023?')).not.toBeInTheDocument())
})

test('falha na rota mostra o erro na conversa e "Tentar de novo" pergunta outra vez', async () => {
  const fetch = backend({
    perguntas: [{ status: 500, corpo: { detail: 'Erro interno no processamento da pergunta.' } }, { corpo: resposta('a1') }],
    auditorias: { a1: auditoria('a1') },
  })
  abrir()

  perguntar('Qual o faturamento em Olinda?')
  expect(await screen.findByText('Não foi possível obter a resposta')).toBeInTheDocument()
  expect(screen.getByText('Erro interno no processamento da pergunta.')).toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }))
  expect(await screen.findByText('Resposta a1')).toBeInTheDocument()
  expect(corpoDas(fetch, '/api/ai/ask').map((corpo) => corpo.message)).toEqual([
    'Qual o faturamento em Olinda?',
    'Qual o faturamento em Olinda?',
  ])
})

test('👍 grava o retorno na auditoria e trava o voto', async () => {
  const fetch = backend({ perguntas: [{ corpo: resposta('a1') }], auditorias: { a1: auditoria('a1') } })
  abrir()
  perguntar('Qual o faturamento em Olinda?')
  await screen.findByText('Resposta a1')

  fireEvent.click(screen.getByRole('button', { name: 'Resposta útil' }))
  expect(await screen.findByText('Obrigado pelo retorno')).toBeInTheDocument()
  expect(corpoDas(fetch, '/api/ai/feedback')).toEqual([{ audit_id: 'a1', feedback: 1 }])
  expect(screen.getByRole('button', { name: 'Resposta não ajudou' })).toBeDisabled()
})

test('recusa honesta aparece com o selo dela e o passo interrompido no grafo', async () => {
  backend({
    perguntas: [{ corpo: resposta('r1', { answer: 'Não consigo responder.', sql: null, selo_confianca: 'recusa_honesta' }) }],
    auditorias: {
      r1: auditoria('r1', {
        rota_escolhida: 'fora_escopo',
        sql_gerado: null,
        linhas_retornadas: 0,
        amostra_resultado_json: '[]',
        passos_execucao: JSON.stringify([
          'Nó 1 — Filtro de segurança: aprovado.',
          'Nó 3 — Escopo LLM: fora (Pergunta sem relação com a distribuidora)',
          'Nó 10 — Recusa emitida: fora_escopo.',
        ]),
      }),
    },
  })
  abrir()
  perguntar('Qual a previsão do tempo?')

  expect(await screen.findByText('Sem resposta segura')).toBeInTheDocument()
  await waitFor(() =>
    expect(passosNoGrafo()).toEqual(['Nó 1: Filtro de segurança', 'Nó 3: Escopo', 'Nó 10: Recusa honesta', 'Nó 12: Auditoria']),
  )
  expect(screen.getAllByText('Interrompido')).toHaveLength(2)
  expect(screen.getByText('Fora do escopo')).toBeInTheDocument()
})

test('"Nova conversa" limpa a conversa e começa outra sessão', async () => {
  const fetch = backend({
    perguntas: [{ corpo: resposta('a1') }, { corpo: resposta('a2') }],
    auditorias: { a1: auditoria('a1'), a2: auditoria('a2') },
  })
  abrir()
  perguntar('Qual o faturamento em Olinda?')
  await screen.findByText('Resposta a1')

  fireEvent.click(screen.getByRole('button', { name: 'Nova conversa' }))
  expect(screen.queryByText('Resposta a1')).not.toBeInTheDocument()
  expect(screen.getByRole('list', { name: 'Sugestões de pergunta' })).toBeInTheDocument()

  perguntar('Qual o faturamento em Recife?')
  await screen.findByText('Resposta a2')
  const [primeira, segunda] = corpoDas(fetch, '/api/ai/ask')
  expect(segunda.session_id).not.toBe(primeira.session_id)
  expect(segunda.history).toEqual([])
})
