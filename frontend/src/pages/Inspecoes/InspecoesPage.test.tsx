import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { getResponse } from 'msw'
import { Route, Routes } from 'react-router'
import { afterEach, beforeEach, expect, test, vi, type MockInstance } from 'vitest'
import { handlers } from '@/mocks/handlers'
import { limparOrdens } from '@/mocks/inspecoes'
import { opcoesFiltrosExemplo } from '@/mocks/opcoes-filtros'
import InspecoesPage from '@/pages/Inspecoes/InspecoesPage'
import { renderizar } from '@/test/renderizar'

// A tela conversa com os dados de exemplo do MSW, que guardam as ordens na memória
let fetch: MockInstance<typeof globalThis.fetch>

beforeEach(() => {
  limparOrdens()
  fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (entrada, init) => {
    const requisicao = new Request(new URL(String(entrada), location.origin), init)
    return (await getResponse(handlers, requisicao)) ?? new Response(null, { status: 404 })
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

function abrir(url = '/inspecoes') {
  renderizar(
    <Routes>
      <Route path="/inspecoes" element={<InspecoesPage />} />
    </Routes>,
    { url, opcoesFiltros: opcoesFiltrosExemplo },
  )
}

test('mostra a fila na prioridade da base, com os motivos em texto', async () => {
  abrir('/inspecoes?municipio=Recife')

  const linhas = await screen.findAllByRole('checkbox')
  expect(linhas).toHaveLength(20)
  expect(String(fetch.mock.calls[0][0])).toContain('/api/inspections/queue?pagina=1&limite=20&municipio=Recife')
  const [primeiraUc] = screen.getAllByRole('link', { name: /^UC9\d{5}$/ })
  expect(primeiraUc).toHaveAttribute('href', expect.stringMatching(/^\/visao-360\/UC9/))
  expect(screen.getAllByText(/· Recife/)).not.toHaveLength(0)
  expect(screen.queryByText(/eletromecanico/)).not.toBeInTheDocument()
})

test('gerar ordens das UCs marcadas e acompanhar até concluir', async () => {
  abrir()

  const [primeira, segunda] = await screen.findAllByRole('checkbox')
  fireEvent.click(primeira)
  fireEvent.click(segunda)
  expect(screen.getByText('2 selecionadas')).toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: 'Gerar ordens de inspeção' }))
  expect(await screen.findByText(/2 ordens de inspeção geradas\./)).toBeInTheDocument()
  // As UCs com ordem mostram a situação no lugar da caixa
  await waitFor(() => expect(screen.getAllByText('Aberta')).toHaveLength(2))

  fireEvent.click(screen.getByRole('tab', { name: /Ordens de inspeção/ }))
  const painel = screen.getByRole('tabpanel')
  fireEvent.click(within(painel).getAllByRole('button', { name: 'Enviar para campo' })[0])
  fireEvent.click(await within(painel).findByRole('button', { name: 'Irregularidade confirmada' }))

  expect(await within(painel).findByText('Concluída')).toBeInTheDocument()
  await waitFor(() => expect(screen.getByText('100%')).toBeInTheDocument())
  expect(screen.getByText('1 de 1 concluída com irregularidade')).toBeInTheDocument()
})

test('cancelar uma ordem', async () => {
  abrir()

  fireEvent.click((await screen.findAllByRole('checkbox'))[0])
  fireEvent.click(screen.getByRole('button', { name: 'Gerar ordens de inspeção' }))
  await screen.findByText(/1 ordem de inspeção gerada\./)

  fireEvent.click(screen.getByRole('tab', { name: /Ordens de inspeção/ }))
  fireEvent.click(await within(screen.getByRole('tabpanel')).findByRole('button', { name: 'Cancelar' }))
  expect(await screen.findByText('Cancelada')).toBeInTheDocument()
})
