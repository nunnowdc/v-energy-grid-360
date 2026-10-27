import { fireEvent, screen, within } from '@testing-library/react'
import { Route, Routes, useLocation } from 'react-router'
import { afterEach, expect, test, vi } from 'vitest'
import { uc360Exemplo } from '@/mocks/uc-360'
import Visao360Page from '@/pages/Visao360/Visao360Page'
import { renderizar } from '@/test/renderizar'

// O gráfico precisa medir a tela, o que o jsdom não faz
vi.mock('@/components/ConsumoDozeMeses/ConsumoDozeMeses', () => ({ default: () => null }))

function Endereco() {
  return <output data-testid="endereco">{useLocation().pathname}</output>
}

function abrir(url: string) {
  renderizar(
    <Routes>
      <Route path="/visao-360/:idUc?" element={<><Visao360Page /><Endereco /></>} />
    </Routes>,
    { url },
  )
}

function responderCom(status: number, corpo: unknown) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(corpo), { status, headers: { 'Content-Type': 'application/json' } }),
  )
}

afterEach(() => {
  vi.restoreAllMocks()
})

test('sem ID, pede para buscar uma UC e não chama a API', () => {
  const fetch = vi.spyOn(globalThis, 'fetch')
  abrir('/visao-360')
  expect(screen.getByText('Busque uma unidade consumidora')).toBeInTheDocument()
  expect(fetch).not.toHaveBeenCalled()
})

test('a busca aceita só o ID completo e abre a UC', () => {
  responderCom(200, uc360Exemplo)
  abrir('/visao-360')
  const campo = screen.getByLabelText('ID da unidade consumidora')
  const busca = screen.getByRole('search')

  fireEvent.change(campo, { target: { value: '123' } })
  fireEvent.submit(busca)
  expect(screen.getByText(/Digite UC seguido de 6 números/)).toBeInTheDocument()
  expect(screen.getByTestId('endereco')).toHaveTextContent('/visao-360')

  // Minúsculas e espaços são aceitos
  fireEvent.change(campo, { target: { value: ' uc000001 ' } })
  fireEvent.submit(busca)
  expect(screen.getByTestId('endereco')).toHaveTextContent('/visao-360/UC000001')
})

test('mostra cadastro, faturas em aberto e os históricos da UC', async () => {
  const fetch = responderCom(200, uc360Exemplo)
  abrir('/visao-360/UC000001')

  expect(await screen.findByText('Maria Exemplo da Silva')).toBeInTheDocument()
  expect(fetch.mock.calls[0][0]).toBe(
    '/api/uc/UC000001/360?pagina_faturas=1&pagina_leituras=1&pagina_interrupcoes=1&pagina_chamados=1&limite=10',
  )
  expect(screen.getByText('Eletromecânico')).toBeInTheDocument()
  expect(screen.getByText('Geração na própria UC')).toBeInTheDocument()
  expect(screen.getByText('em 2 faturas')).toBeInTheDocument()
  expect(screen.getByText('Atrasada')).toBeInTheDocument()

  const abas = screen.getAllByRole('tab').map((aba) => aba.textContent)
  expect(abas).toEqual(['Faturas1', 'Leituras0', 'Interrupções1', 'Chamados0'])

  fireEvent.click(screen.getByRole('tab', { name: /Interrupções/ }))
  const painel = screen.getByRole('tabpanel')
  expect(within(painel).getByText('Vegetação')).toBeInTheDocument()
  expect(within(painel).getByText('02/03/2026 10:00')).toBeInTheDocument()
})

test('UC que não existe mostra "não encontrada"', async () => {
  responderCom(404, { detail: 'Unidade consumidora não encontrada' })
  abrir('/visao-360/UC999999')
  expect(await screen.findByText('Unidade consumidora não encontrada')).toBeInTheDocument()
})

test('ID fora do formato nem chega a chamar a API', () => {
  const fetch = vi.spyOn(globalThis, 'fetch')
  abrir('/visao-360/abc')
  expect(screen.getByText('Unidade consumidora não encontrada')).toBeInTheDocument()
  expect(fetch).not.toHaveBeenCalled()
})
