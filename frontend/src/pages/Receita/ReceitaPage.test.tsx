import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { Route, Routes } from 'react-router'
import { afterEach, expect, test, vi } from 'vitest'
import type { DecomposicaoReceita, VariacaoReceita } from '@/hooks/use-receita'
import { opcoesFiltrosExemplo } from '@/mocks/opcoes-filtros'
import ReceitaPage from '@/pages/Receita/ReceitaPage'
import { renderizar } from '@/test/renderizar'

// O gráfico precisa medir a tela, o que o jsdom não faz
vi.mock('@/components/PonteReceita/PonteReceita', () => ({ default: () => null }))

// Recorte sem nenhuma linha na Gold: a API manda tudo nulo
const vazio: DecomposicaoReceita = {
  receita_p0: null,
  receita_p1: null,
  kwh_p0: null,
  kwh_p1: null,
  ucs_p0: null,
  ucs_p1: null,
  preco_p0: null,
  preco_p1: null,
  efeito_volume: null,
  efeito_preco: null,
}

const decomposicao = (valores: Partial<DecomposicaoReceita>): DecomposicaoReceita => ({
  receita_p0: 100_000_000,
  receita_p1: 110_000_000,
  kwh_p0: 125_000_000,
  kwh_p1: 120_000_000,
  ucs_p0: 1000,
  ucs_p1: 1100,
  preco_p0: 0.8,
  preco_p1: 0.92,
  efeito_volume: -4_000_000,
  efeito_preco: 14_000_000,
  ...valores,
})

// Números redondos inventados para conferir as contas da tela
const receita: VariacaoReceita = {
  periodo_p0: { inicio: '2022-07', fim: '2023-06' },
  periodo_p1: { inicio: '2025-07', fim: '2026-06' },
  total: decomposicao({}),
  por_gd: [
    { possui_gd: false, ...decomposicao({ efeito_volume: -1_000_000 }) },
    { possui_gd: true, ...decomposicao({ efeito_volume: -3_000_000 }) },
  ],
  detalhamento: {
    nivel: 'municipio',
    linhas: [
      { nome: 'Olinda', ...decomposicao({ efeito_volume: -500_000 }) },
      { nome: 'Recife', ...decomposicao({ efeito_volume: -2_500_000 }) },
    ],
  },
}

function abrir(url: string) {
  return renderizar(
    <Routes>
      <Route path="/receita" element={<ReceitaPage />} />
    </Routes>,
    { url, opcoesFiltros: opcoesFiltrosExemplo },
  )
}

function responderCom(corpo: unknown) {
  return vi
    .spyOn(globalThis, 'fetch')
    .mockImplementation(async () =>
      new Response(JSON.stringify(corpo), { status: 200, headers: { 'Content-Type': 'application/json' } }),
    )
}

const enderecosChamados = (fetch: ReturnType<typeof responderCom>) => fetch.mock.calls.map((chamada) => chamada[0])

afterEach(() => {
  vi.restoreAllMocks()
})

test('sem escolha, compara o primeiro ano com os últimos 12 meses e mostra os KPIs', async () => {
  const fetch = responderCom(receita)
  abrir('/receita')

  expect(await screen.findByText('Consumo medido -4,0%')).toBeInTheDocument()
  expect(enderecosChamados(fetch)).toEqual(['/api/metrics/revenue-variance?inicio_p0=2022-07&fim_p0=2023-06&inicio_p1=2025-07&fim_p1=2026-06'])
  // Mesmos meses do ano dos dois lados: sem aviso de sazonalidade
  expect(screen.queryByText(/Meses diferentes do ano/)).not.toBeInTheDocument()
  // Na barra de filtros e na frase acima dos cards
  expect(screen.getAllByText('jul/2022 – jun/2023')).toHaveLength(2)
  expect(screen.getAllByText('jul/2025 – jun/2026')).toHaveLength(2)
  // Receita: 110 mi contra 100 mi
  expect(screen.getAllByText('+10,0%', { exact: false })).not.toHaveLength(0)
  // 3 mi de 4 mi de efeito volume
  expect(screen.getByText('75% do efeito volume vem das UCs com geração própria.')).toBeInTheDocument()
})

test('manda os filtros escolhidos', async () => {
  const fetch = responderCom(receita)
  abrir('/receita?base_de=2023-01&base_ate=2023-03&comparado_de=2025-07&municipio=Olinda&bairro=Rio+Doce&classe=RURAL')

  await screen.findByText('Consumo medido -4,0%')
  expect(enderecosChamados(fetch)).toEqual([
    '/api/metrics/revenue-variance?inicio_p0=2023-01&fim_p0=2023-03&inicio_p1=2025-07&fim_p1=2025-09&municipio=Olinda&bairro=Rio+Doce&classe=RURAL',
  ])
})

test('com só o base escolhido, o comparado vai para os mesmos meses do último ano', async () => {
  const fetch = responderCom(receita)
  abrir('/receita?base_de=2023-01&base_ate=2023-03')

  await screen.findByText('Consumo medido -4,0%')
  expect(enderecosChamados(fetch)).toEqual([
    '/api/metrics/revenue-variance?inicio_p0=2023-01&fim_p0=2023-03&inicio_p1=2026-01&fim_p1=2026-03',
  ])
})

test('períodos com meses diferentes do ano mostram o aviso de sazonalidade', async () => {
  responderCom({
    ...receita,
    periodo_p0: { inicio: '2023-01', fim: '2023-03' },
    periodo_p1: { inicio: '2025-07', fim: '2025-09' },
  })
  abrir('/receita?base_de=2023-01&base_ate=2023-03&comparado_de=2025-07')
  expect(await screen.findByText(/Meses diferentes do ano/)).toBeInTheDocument()
})

test('a tabela começa pela maior perda de volume e clicar numa linha detalha', async () => {
  const fetch = responderCom(receita)
  abrir('/receita')

  const linhas = await screen.findAllByRole('button', { name: /^(Olinda|Recife)$/ })
  expect(linhas.map((linha) => linha.textContent)).toEqual(['Recife', 'Olinda'])

  fireEvent.click(linhas[0])
  await waitFor(() => expect(enderecosChamados(fetch)).toContain('/api/metrics/revenue-variance?inicio_p0=2022-07&fim_p0=2023-06&inicio_p1=2025-07&fim_p1=2026-06&municipio=Recife'))
})

test('cada linha diz o que o clique faz, e as variações têm cor de boa ou ruim', async () => {
  responderCom(receita)
  abrir('/receita')

  await screen.findAllByRole('button', { name: /^(Olinda|Recife)$/ })
  expect(screen.getAllByText('Ver bairros')).toHaveLength(2)
  // Efeito volume de Recife tira receita (vermelho); o efeito preço soma (verde)
  expect(screen.getByText('-R$ 2,5 mi')).toHaveClass('text-negativo')
  expect(screen.getAllByText('+R$ 14 mi')[0]).toHaveClass('text-positivo')
})

test('descer pela tabela preenche o filtro do topo, que libera o bairro', async () => {
  responderCom(receita)
  abrir('/receita')

  expect(screen.getByRole('combobox', { name: 'Bairro: Escolha um município' })).toBeDisabled()
  fireEvent.click((await screen.findAllByRole('button', { name: 'Recife' }))[0])

  expect(await screen.findByRole('combobox', { name: 'Município: Recife' })).toBeInTheDocument()
  expect(screen.getByRole('combobox', { name: 'Bairro: Todos' })).toBeEnabled()
})

test('o "Voltar a todos os municípios", junto da tabela, tira só município e bairro', async () => {
  const fetch = responderCom(receita)
  abrir('/receita?municipio=Recife&bairro=Pina&classe=RURAL')

  fireEvent.click(await screen.findByRole('button', { name: 'Voltar a todos os municípios' }))
  await waitFor(() =>
    expect(enderecosChamados(fetch)).toContain(
      '/api/metrics/revenue-variance?inicio_p0=2022-07&fim_p0=2023-06&inicio_p1=2025-07&fim_p1=2026-06&classe=RURAL',
    ),
  )
  expect(screen.queryByRole('button', { name: 'Voltar a todos os municípios' })).not.toBeInTheDocument()
})

test('a trilha volta um nível', async () => {
  const fetch = responderCom(receita)
  abrir('/receita?municipio=Recife&bairro=Pina')

  const trilha = await screen.findByRole('navigation', { name: 'Nível do detalhamento' })
  fireEvent.click(within(trilha).getByRole('button', { name: 'Recife' }))
  await waitFor(() => expect(enderecosChamados(fetch)).toContain('/api/metrics/revenue-variance?inicio_p0=2022-07&fim_p0=2023-06&inicio_p1=2025-07&fim_p1=2026-06&municipio=Recife'))
})

test('quando só as UCs com geração própria perdem volume, a frase conta isso', async () => {
  responderCom({
    ...receita,
    por_gd: [
      { possui_gd: false, ...decomposicao({ efeito_volume: 1_000_000 }) },
      { possui_gd: true, ...decomposicao({ efeito_volume: -5_000_000 }) },
    ],
  })
  abrir('/receita')

  expect(await screen.findByText(/A queda de volume vem das UCs com geração própria/)).toBeInTheDocument()
})

test('bairro sem UC com geração própria mostra o grupo vazio, sem zeros', async () => {
  responderCom({
    ...receita,
    por_gd: [{ possui_gd: false, ...decomposicao({}) }, { possui_gd: true, ...vazio }],
  })
  abrir('/receita?municipio=Recife&bairro=Pina')

  expect(await screen.findByText('Nenhuma UC neste recorte.')).toBeInTheDocument()
  expect(screen.queryByText(/do efeito volume vem/)).not.toBeInTheDocument()
})

test('recorte sem dados na base avisa em vez de mostrar zeros', async () => {
  responderCom({
    ...receita,
    total: vazio,
    por_gd: [
      { possui_gd: false, ...vazio },
      { possui_gd: true, ...vazio },
    ],
    detalhamento: { nivel: 'classe', linhas: [] },
  })
  abrir('/receita?municipio=Recife&bairro=Pina&classe=RURAL')

  expect(await screen.findAllByText('Nenhuma receita para esses filtros.')).toHaveLength(4)
  expect(screen.queryByText(/R\$/)).not.toBeInTheDocument()
})
