import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { Route, Routes } from 'react-router'
import { afterEach, expect, test, vi } from 'vitest'
import type { DecomposicaoReceita, VariacaoReceita } from '@/hooks/use-receita'
import { opcoesFiltrosExemplo } from '@/mocks/opcoes-filtros'
import ReceitaPage from '@/pages/Receita/ReceitaPage'
import { renderizar } from '@/test/renderizar'

// O gráfico precisa medir a tela, o que o jsdom não faz
vi.mock('@/components/PonteReceita/PonteReceita', () => ({ default: () => null }))

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

test('mostra os períodos fixos, os KPIs e a parte das UCs com geração própria', async () => {
  const fetch = responderCom(receita)
  abrir('/receita')

  expect(await screen.findByText('jul/2022 – jun/2023')).toBeInTheDocument()
  expect(enderecosChamados(fetch)).toEqual(['/api/metrics/revenue-variance'])
  expect(screen.getByText('jul/2025 – jun/2026')).toBeInTheDocument()
  // Receita: 110 mi contra 100 mi
  expect(screen.getAllByText('+10,0%', { exact: false })).not.toHaveLength(0)
  expect(screen.getByText('Consumo medido -4,0%')).toBeInTheDocument()
  // 3 mi de 4 mi de efeito volume
  expect(screen.getByText('75%')).toBeInTheDocument()
})

test('manda os filtros escolhidos', async () => {
  const fetch = responderCom(receita)
  abrir('/receita?municipio=Olinda&bairro=Rio+Doce&classe=RURAL')

  await screen.findByText('jul/2022 – jun/2023')
  expect(enderecosChamados(fetch)).toEqual([
    '/api/metrics/revenue-variance?municipio=Olinda&bairro=Rio+Doce&classe=RURAL',
  ])
})

test('a tabela começa pela maior perda de volume e clicar numa linha detalha', async () => {
  const fetch = responderCom(receita)
  abrir('/receita')

  const linhas = await screen.findAllByRole('button', { name: /^(Olinda|Recife)$/ })
  expect(linhas.map((linha) => linha.textContent)).toEqual(['Recife', 'Olinda'])

  fireEvent.click(linhas[0])
  await waitFor(() => expect(enderecosChamados(fetch)).toContain('/api/metrics/revenue-variance?municipio=Recife'))
})

test('a trilha volta um nível', async () => {
  const fetch = responderCom(receita)
  abrir('/receita?municipio=Recife&bairro=Pina')

  const trilha = await screen.findByRole('navigation', { name: 'Nível do detalhamento' })
  fireEvent.click(within(trilha).getByRole('button', { name: 'Recife' }))
  await waitFor(() => expect(enderecosChamados(fetch)).toContain('/api/metrics/revenue-variance?municipio=Recife'))
})
