import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { Route, Routes } from 'react-router'
import { afterEach, beforeEach, expect, test, vi, type MockInstance } from 'vitest'
import type { ItemFila } from '@/hooks/use-fila-inspecao'
import type { OrdemInspecao, StatusOrdem } from '@/hooks/use-ordens-inspecao'
import { opcoesFiltrosExemplo } from '@/mocks/opcoes-filtros'
import InspecoesPage from '@/pages/Inspecoes/InspecoesPage'
import { renderizar } from '@/test/renderizar'

// UCs inventadas (fora da faixa da base), na prioridade da Gold
const fila: Omit<ItemFila, 'ordem_aberta'>[] = [
  {
    prioridade: 1,
    id_uc: 'UC900001',
    score: 70,
    motivo_suspeita: 'Queda de consumo >= 50% (+40); Medidor eletromecanico (+15); Leituras estimadas >= 50% (+15)',
    kwh_recuperavel_estimado_ano: 3600,
    municipio: 'Recife',
    bairro: 'Pina',
    classe: 'RESIDENCIAL',
  },
  {
    prioridade: 2,
    id_uc: 'UC900002',
    score: 55,
    motivo_suspeita: 'Queda de consumo >= 50% (+40); Medidor eletromecanico (+15)',
    kwh_recuperavel_estimado_ano: 2400,
    municipio: 'Recife',
    bairro: 'Ibura',
    classe: 'COMERCIAL',
  },
  {
    prioridade: 3,
    id_uc: 'UC900003',
    score: 30,
    motivo_suspeita: 'Queda de consumo >= 30% (+30)',
    kwh_recuperavel_estimado_ano: 0,
    municipio: 'Olinda',
    bairro: 'Casa Caiada',
    classe: 'RESIDENCIAL',
  },
]

// Backend de mentira com as regras da rota real: gerar é tudo ou nada (409 se uma
// UC do lote já tem ordem aberta), a ordem anda aberta → em campo → concluída
// (ou cancelada antes de concluir) e a hora vem em UTC
let ordens: OrdemInspecao[]
let fetch: MockInstance<typeof globalThis.fetch>

const permitidas: Partial<Record<StatusOrdem, StatusOrdem[]>> = {
  ABERTA: ['EM_CAMPO', 'CANCELADA'],
  EM_CAMPO: ['CONCLUIDA', 'CANCELADA'],
}

const ordemAberta = (idUc: string) =>
  ordens.find((ordem) => ordem.id_uc === idUc && (ordem.status === 'ABERTA' || ordem.status === 'EM_CAMPO'))

function criarOrdem(idUc: string) {
  const { municipio, bairro } = fila.find((item) => item.id_uc === idUc)!
  const ordem: OrdemInspecao = {
    id_ordem: `OI-${String(ordens.length + 1).padStart(5, '0')}`,
    id_uc: idUc,
    municipio,
    bairro,
    status: 'ABERTA',
    resultado: null,
    criada_em: '2026-10-28T21:09:39.757316Z',
  }
  ordens = [ordem, ...ordens]
  return ordem
}

function backend(metodo: string, url: URL, corpo: unknown): [number, unknown] {
  const municipio = url.searchParams.get('municipio')
  const doRecorte = (item: { municipio: string }) => !municipio || item.municipio === municipio

  if (url.pathname === '/api/inspections/queue') {
    const recorte = fila.filter(doRecorte)
    return [
      200,
      {
        data_referencia: '2026-06-01',
        resumo: {
          ucs: recorte.length,
          kwh_recuperavel_estimado_ano: recorte.reduce((soma, item) => soma + item.kwh_recuperavel_estimado_ano, 0),
        },
        pagina: 1,
        limite: 20,
        total: recorte.length,
        itens: recorte.map((item) => {
          const ordem = ordemAberta(item.id_uc)
          return { ...item, ordem_aberta: ordem ? { id_ordem: ordem.id_ordem, status: ordem.status } : null }
        }),
      },
    ]
  }
  if (url.pathname === '/api/inspections/orders') {
    return [200, { itens: ordens.filter(doRecorte) }]
  }
  if (url.pathname === '/api/inspections/order') {
    const { ids_uc } = corpo as { ids_uc: string[] }
    const comOrdem = ids_uc.filter(ordemAberta)
    if (comOrdem.length > 0) {
      return [409, { detail: `Já existe ordem ativa para as UCs: ${comOrdem.join(', ')}` }]
    }
    return [201, { ordens: ids_uc.map(criarOrdem) }]
  }

  // PATCH e DELETE /api/inspections/{id_ordem}
  const ordem = ordens.find((item) => url.pathname === `/api/inspections/${item.id_ordem}`)
  if (!ordem) {
    return [404, { detail: 'Ordem não encontrada' }]
  }
  const mudanca = {
    resultado: null,
    ...(metodo === 'DELETE' ? { status: 'CANCELADA' } : (corpo as object)),
  } as Pick<OrdemInspecao, 'status' | 'resultado'>
  if (!permitidas[ordem.status]?.includes(mudanca.status)) {
    return [409, { detail: 'Transição de ordem inválida' }]
  }
  Object.assign(ordem, mudanca)
  return [200, ordem]
}

beforeEach(() => {
  ordens = []
  fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (entrada, init) => {
    const url = new URL(String(entrada), location.origin)
    const corpo = typeof init?.body === 'string' ? JSON.parse(init.body) : undefined
    const [status, resposta] = backend(init?.method ?? 'GET', url, corpo)
    return new Response(JSON.stringify(resposta), { status, headers: { 'Content-Type': 'application/json' } })
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

const enderecosChamados = () => fetch.mock.calls.map(([entrada]) => String(entrada))

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

  expect(await screen.findAllByRole('checkbox')).toHaveLength(2)
  expect(enderecosChamados()).toContain('/api/inspections/queue?pagina=1&limite=20&municipio=Recife')
  const ucs = screen.getAllByRole('link', { name: /^UC9\d{5}$/ })
  expect(ucs.map((link) => link.textContent)).toEqual(['UC900001', 'UC900002'])
  expect(ucs[0]).toHaveAttribute('href', '/visao-360/UC900001')
  expect(screen.getAllByText('Medidor eletromecânico')).toHaveLength(2)
  expect(screen.queryByText(/eletromecanico/)).not.toBeInTheDocument()
})

test('as ordens seguem os mesmos filtros da fila', async () => {
  abrir('/inspecoes?municipio=Recife&bairro=Pina&classe=RESIDENCIAL')

  await screen.findAllByRole('checkbox')
  expect(enderecosChamados()).toContain('/api/inspections/orders?municipio=Recife&bairro=Pina&classe=RESIDENCIAL')
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
  // A hora vem em UTC e aparece no horário de Recife
  expect(within(painel).getAllByText('28/10/2026 18:09')).toHaveLength(2)
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

test('UC que ganhou ordem com a tela aberta: nada é gerado e ela sai da seleção', async () => {
  abrir()

  const [primeira, segunda] = await screen.findAllByRole('checkbox')
  fireEvent.click(primeira)
  fireEvent.click(segunda)
  // Outra pessoa da equipe gera a ordem da segunda UC antes
  criarOrdem('UC900002')

  fireEvent.click(screen.getByRole('button', { name: 'Gerar ordens de inspeção' }))
  expect(
    await screen.findByText('Nenhuma ordem foi gerada: UC900002 já tem ordem aberta e saiu da seleção.'),
  ).toBeInTheDocument()
  expect(screen.getByText('1 selecionada')).toBeInTheDocument()
  // A fila recarrega e mostra a ordem no lugar da caixa
  await waitFor(() => expect(screen.getAllByRole('checkbox')).toHaveLength(2))
  expect(screen.getByText('Aberta')).toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: 'Gerar ordens de inspeção' }))
  expect(await screen.findByText(/1 ordem de inspeção gerada\./)).toBeInTheDocument()
  expect(ordens.map((ordem) => ordem.id_uc)).toEqual(['UC900001', 'UC900002'])
})

test('ordem que outra pessoa mudou antes: avisa e mostra a situação atual', async () => {
  criarOrdem('UC900001')
  abrir()

  fireEvent.click(await screen.findByRole('tab', { name: /Ordens de inspeção/ }))
  const painel = screen.getByRole('tabpanel')
  const enviar = await within(painel).findByRole('button', { name: 'Enviar para campo' })
  ordens[0].status = 'CANCELADA'

  fireEvent.click(enviar)
  expect(
    await within(painel).findByText('Essa ordem já tinha mudado de situação. A lista foi atualizada.'),
  ).toBeInTheDocument()
  expect(await within(painel).findByText('Cancelada')).toBeInTheDocument()
})
