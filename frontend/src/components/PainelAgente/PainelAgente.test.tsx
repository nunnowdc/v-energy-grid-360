import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { useLocation } from 'react-router'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import PainelAgente from '@/components/PainelAgente/PainelAgente'
import type { Perfil } from '@/config/perfis'
import type { AuditoriaAgente, RespostaAgente } from '@/hooks/use-agente-ia'
import { opcoesFiltrosExemplo } from '@/mocks/opcoes-filtros'
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

const auditoriasBuscadas = (fetch: ReturnType<typeof backend>) =>
  fetch.mock.calls.map(([url]) => String(url)).filter((url) => url.startsWith('/api/ai/audit/'))

// Mostra o endereço atual, para conferir a tela que o agente abriu
function Endereco() {
  const { pathname, search } = useLocation()
  return <output aria-label="Endereço">{pathname + search}</output>
}

function abrir({
  url = '/receita',
  aberto = true,
  comOpcoes = false,
  perfil = 'ADMIN_TI' as Perfil,
} = {}) {
  const aoFechar = vi.fn()
  renderizar(
    <>
      <PainelAgente aberto={aberto} aoFechar={aoFechar} />
      <Endereco />
    </>,
    { url, opcoesFiltros: comOpcoes ? opcoesFiltrosExemplo : undefined, perfil },
  )
  return { aoFechar }
}

const endereco = () => screen.getByLabelText('Endereço').textContent

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
  vi.spyOn(crypto, 'randomUUID').mockImplementation(
    () => `00000000-0000-4000-8000-00000000000${sequencia++}` as `${string}-${string}-${string}-${string}-${string}`,
  )
})

afterEach(() => {
  vi.restoreAllMocks()
})

test('conversa vazia oferece sugestões e já deixa o cursor na pergunta', () => {
  backend({ perguntas: [], auditorias: {} })
  abrir()
  expect(screen.getByRole('complementary', { name: 'Agente de IA' })).toBeInTheDocument()
  expect(within(screen.getByRole('list', { name: 'Sugestões de pergunta' })).getAllByRole('button')).toHaveLength(3)
  expect(screen.getByLabelText('Sua pergunta')).toHaveFocus()
  expect(screen.getByRole('button', { name: 'Nova conversa' })).toBeDisabled()
})

test('a sugestão vira pergunta com o contexto da tela, e a resposta chega com selo e tempo', async () => {
  const fetch = backend({ perguntas: [{ corpo: resposta('a1') }], auditorias: { a1: auditoria('a1') } })
  abrir({ url: '/receita' })

  fireEvent.click(screen.getByRole('button', { name: 'Qual o faturamento em Recife no ano de 2024?' }))
  expect(screen.getByText(/Analisando a pergunta/)).toBeInTheDocument()
  expect(await screen.findByText('Resposta a1')).toBeInTheDocument()

  expect(corpoDas(fetch, '/api/ai/ask')).toEqual([
    {
      session_id: '00000000-0000-4000-8000-000000000000',
      message: 'Qual o faturamento em Recife no ano de 2024?',
      context: { page: 'receita' },
      history: [],
    },
  ])
  expect(screen.getByText('Consulta certificada')).toBeInTheDocument()
  expect(screen.getByText('7,4 s')).toBeInTheDocument()
})

test('na Visão 360 o contexto leva a UC aberta, e o "/" é a tela de Indicadores', async () => {
  const fetch = backend({ perguntas: [{ corpo: resposta('a1') }], auditorias: {} })
  abrir({ url: '/visao-360/UC100000' })
  perguntar('Essa UC tem fatura atrasada?')
  await screen.findByText('Resposta a1')
  expect(corpoDas(fetch, '/api/ai/ask')[0].context).toEqual({ page: 'visao-360', id_uc: 'UC100000' })
  document.body.innerHTML = ''

  const outro = backend({ perguntas: [{ corpo: resposta('a2') }], auditorias: {} })
  abrir({ url: '/' })
  perguntar('Qual a receita total?')
  await screen.findByText('Resposta a2')
  expect(corpoDas(outro, '/api/ai/ask').at(-1).context).toEqual({ page: 'indicadores' })
})

test('o passo a passo só aparece, e só é buscado, ao clicar em "Ver o passo a passo"', async () => {
  const fetch = backend({ perguntas: [{ corpo: resposta('a1') }], auditorias: { a1: auditoria('a1') } })
  abrir()
  perguntar('Qual o faturamento em Olinda?')
  await screen.findByText('Resposta a1')

  expect(screen.queryByRole('region', { name: 'Como a IA chegou nisso?' })).not.toBeInTheDocument()
  expect(auditoriasBuscadas(fetch)).toEqual([])

  const ver = screen.getByRole('button', { name: 'Ver o passo a passo' })
  fireEvent.click(ver)
  expect(ver).toHaveAttribute('aria-expanded', 'true')
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
  expect(auditoriasBuscadas(fetch)).toEqual(['/api/ai/audit/a1'])
  // A consulta aparece no nó que a produziu e a amostra no nó da execução
  expect(screen.getByText(/FROM agg_receita_mensal/)).toBeInTheDocument()
  expect(screen.getByRole('cell', { name: '1.500,5' })).toBeInTheDocument()
  expect(screen.getByText('Consulta aos dados')).toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: 'Esconder o passo a passo' }))
  expect(screen.queryByRole('list', { name: 'Passos do agente' })).not.toBeInTheDocument()
})

test('só o ADMIN_TI vê o passo a passo; os outros perfis perguntam e avaliam normalmente', async () => {
  const fetch = backend({ perguntas: [{ corpo: resposta('a1') }], auditorias: { a1: auditoria('a1') } })
  abrir({ perfil: 'DIRETORIA' })
  perguntar('Qual o faturamento em Olinda?')

  expect(await screen.findByText('Resposta a1')).toBeInTheDocument()
  // Quem pergunta não vai no corpo: o backend usa a conta do cookie
  expect(corpoDas(fetch, '/api/ai/ask')[0]).not.toHaveProperty('user_id')
  expect(screen.queryByRole('button', { name: 'Ver o passo a passo' })).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Resposta útil' })).toBeInTheDocument()
  expect(auditoriasBuscadas(fetch)).toEqual([])
})

test('a pergunta seguinte leva o histórico, e cada resposta abre o próprio passo a passo', async () => {
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

  const [, verSegunda] = screen.getAllByRole('button', { name: 'Ver o passo a passo' })
  fireEvent.click(verSegunda)
  expect(await screen.findByText('Qual o faturamento em Olinda em 2023?')).toBeInTheDocument()
  expect(auditoriasBuscadas(fetch)).toEqual(['/api/ai/audit/a2'])
})

test('falha na rota mostra o erro na conversa e "Tentar de novo" pergunta outra vez', async () => {
  const fetch = backend({
    perguntas: [{ status: 500, corpo: { detail: 'Erro interno no processamento da pergunta.' } }, { corpo: resposta('a1') }],
    auditorias: {},
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
  const fetch = backend({ perguntas: [{ corpo: resposta('a1') }], auditorias: {} })
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
  fireEvent.click(screen.getByRole('button', { name: 'Ver o passo a passo' }))
  await waitFor(() =>
    expect(passosNoGrafo()).toEqual(['Nó 1: Filtro de segurança', 'Nó 3: Escopo', 'Nó 10: Recusa honesta', 'Nó 12: Auditoria']),
  )
  expect(screen.getAllByText('Interrompido')).toHaveLength(2)
  expect(screen.getByText('Fora do escopo')).toBeInTheDocument()
})

test('"Nova conversa" limpa a conversa e começa outra sessão', async () => {
  const fetch = backend({ perguntas: [{ corpo: resposta('a1') }, { corpo: resposta('a2') }], auditorias: {} })
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

test('a resposta em Markdown aparece formatada, sem os asteriscos', async () => {
  backend({
    perguntas: [{ corpo: resposta('d1', { answer: '**FEC** é a frequência.\n\n- por UC\n- em `agg_continuidade`' }) }],
    auditorias: {},
  })
  abrir()
  perguntar('O que é FEC?')

  expect(await screen.findByText('FEC', { selector: 'strong' })).toBeInTheDocument()
  expect(screen.getByText('agg_continuidade', { selector: 'code' })).toBeInTheDocument()
  expect(screen.getAllByRole('listitem').map((item) => item.textContent)).toEqual(['por UC', 'em agg_continuidade'])
  expect(screen.queryByText(/\*\*/)).not.toBeInTheDocument()
})

test('a resposta leva o dashboard para a tela e os filtros que o agente escolheu', async () => {
  backend({
    perguntas: [
      {
        corpo: resposta('a1', {
          sql: "SELECT SUM(receita_faturada) FROM agg_receita_mensal WHERE unaccent(lower(municipio)) = unaccent(lower('recife'))",
          dashboard: { tela: 'indicadores', filtros: { municipio: 'recife', bairro: null } },
        }),
      },
    ],
    auditorias: {},
  })
  abrir({ url: '/continuidade?base_de=2025-07&base_ate=2025-12', comOpcoes: true })
  perguntar('Qual o faturamento em Recife no ano de 2024?')

  await screen.findByText('Resposta a1')
  // O React Router troca de tela com prioridade baixa: pode chegar um instante depois da resposta
  await waitFor(() => expect(endereco()).toBe('/?municipio=Recife'))
  // O link reabre essa visão se a pessoa sair dela
  expect(screen.getByRole('link', { name: 'No dashboard: Indicadores · Recife' })).toHaveAttribute(
    'href',
    '/?municipio=Recife',
  )
})

test('com consulta sem tela no portal, o dashboard fica como está', async () => {
  backend({
    perguntas: [
      { corpo: resposta('a1', { sql: 'SELECT AVG(tempo_resolucao_h) FROM fact_atendimentos', dashboard: null }) },
    ],
    auditorias: {},
  })
  abrir({ url: '/continuidade', comOpcoes: true })
  // O assunto da pergunta seria Indicadores, mas quem decide é a consulta
  perguntar('Qual o tempo médio de atendimento das UCs?')

  await screen.findByText('Resposta a1')
  expect(endereco()).toBe('/continuidade')
  expect(screen.queryByRole('link', { name: /No dashboard/ })).not.toBeInTheDocument()
})

test('resposta de documentação, sem consulta, abre a tela do assunto da pergunta', async () => {
  backend({
    perguntas: [{ corpo: resposta('d1', { sql: null, selo_confianca: 'documental_rag', dashboard: null }) }],
    auditorias: {},
  })
  abrir({ url: '/receita', comOpcoes: true })
  perguntar('O que é DEC e FEC?')

  await screen.findByText('Resposta d1')
  await waitFor(() => expect(endereco()).toBe('/continuidade'))
})

test('recusa honesta não mexe no dashboard', async () => {
  backend({
    perguntas: [{ corpo: resposta('r1', { answer: 'Não sei.', sql: null, selo_confianca: 'recusa_honesta' }) }],
    auditorias: {},
  })
  abrir({ url: '/continuidade', comOpcoes: true })
  perguntar('Qual o faturamento em Recife?')

  await screen.findByText('Não sei.')
  expect(endereco()).toBe('/continuidade')
  expect(screen.queryByRole('link', { name: /No dashboard/ })).not.toBeInTheDocument()
})

test('fechado, o painel some da tela; o X e o Esc pedem para fechar', () => {
  backend({ perguntas: [], auditorias: {} })
  const { aoFechar } = abrir({ aberto: false })
  expect(screen.queryByRole('complementary', { name: 'Agente de IA' })).not.toBeInTheDocument()
  document.body.innerHTML = ''

  const aberto = abrir()
  fireEvent.click(screen.getByRole('button', { name: 'Fechar o agente' }))
  fireEvent.keyDown(screen.getByLabelText('Sua pergunta'), { key: 'Escape' })
  expect(aberto.aoFechar).toHaveBeenCalledTimes(2)
  expect(aoFechar).not.toHaveBeenCalled()
})
