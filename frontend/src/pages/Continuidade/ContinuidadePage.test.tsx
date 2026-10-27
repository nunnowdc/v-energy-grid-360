import { fireEvent, screen, waitFor } from '@testing-library/react'
import { getResponse } from 'msw'
import { Route, Routes } from 'react-router'
import { afterEach, beforeEach, expect, test, vi, type MockInstance } from 'vitest'
import { handlers } from '@/mocks/handlers'
import { opcoesFiltrosExemplo } from '@/mocks/opcoes-filtros'
import ContinuidadePage from '@/pages/Continuidade/ContinuidadePage'
import { renderizar } from '@/test/renderizar'

// O gráfico precisa medir a tela, o que o jsdom não faz
vi.mock('@/components/GraficosMensais/GraficosMensais', () => ({ default: () => null }))

// A tela conversa com os dados de exemplo do MSW
let fetch: MockInstance<typeof globalThis.fetch>

beforeEach(() => {
  fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (entrada, init) => {
    const requisicao = new Request(new URL(String(entrada), location.origin), init)
    return (await getResponse(handlers, requisicao)) ?? new Response(null, { status: 404 })
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

function abrir(url = '/continuidade') {
  renderizar(
    <Routes>
      <Route path="/continuidade" element={<ContinuidadePage />} />
    </Routes>,
    { url, opcoesFiltros: opcoesFiltrosExemplo },
  )
}

const enderecos = () => fetch.mock.calls.map((chamada) => String(chamada[0]))

test('sem filtro, pede os últimos 12 meses e avisa que DEC e FEC são do alimentador inteiro', async () => {
  abrir()

  expect(await screen.findByText('Piores alimentadores')).toBeInTheDocument()
  await screen.findAllByRole('button', { name: /^ALM-/ })
  expect(enderecos()).toEqual(['/api/network/continuity?inicio=2025-07&fim=2026-06'])
  expect(screen.getByText(/DEC e FEC são sempre do alimentador inteiro/)).toBeInTheDocument()
  // Os 8 alimentadores do exemplo cabem sem "Mostrar todos"
  expect(screen.getAllByRole('button', { name: /^ALM-/ })).toHaveLength(8)
})

test('clicar num alimentador do ranking filtra a tela por ele', async () => {
  abrir('/continuidade?municipio=Olinda')

  const [primeiro] = await screen.findAllByRole('button', { name: /^ALM-OLI/ })
  const codigo = primeiro.textContent!
  fireEvent.click(primeiro)

  await waitFor(() =>
    expect(enderecos()).toContain(
      `/api/network/continuity?inicio=2025-07&fim=2026-06&municipio=Olinda&alimentador=${codigo}`,
    ),
  )
})

test('a causa filtra só as ocorrências', async () => {
  abrir('/continuidade?meses=3&causa=VEGETACAO')

  expect(await screen.findByText('Só vegetação')).toBeInTheDocument()
  expect(enderecos()[0]).toBe('/api/network/continuity?inicio=2026-04&fim=2026-06&causa=VEGETACAO')
  expect(screen.queryByText('Climática')).not.toBeInTheDocument()
  expect(screen.getAllByRole('button', { name: /^ALM-/ })).toHaveLength(8)
})
