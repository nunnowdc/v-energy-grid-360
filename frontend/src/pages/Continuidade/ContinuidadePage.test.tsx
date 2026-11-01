import { fireEvent, screen, waitFor } from '@testing-library/react'
import { Route, Routes } from 'react-router'
import { afterEach, beforeEach, expect, test, vi, type MockInstance } from 'vitest'
import type { AlimentadorContinuidade, ContinuidadeRede } from '@/hooks/use-continuidade'
import { opcoesFiltrosExemplo } from '@/mocks/opcoes-filtros'
import ContinuidadePage from '@/pages/Continuidade/ContinuidadePage'
import { renderizar } from '@/test/renderizar'

// O gráfico precisa medir a tela, o que o jsdom não faz
vi.mock('@/components/GraficosMensais/GraficosMensais', () => ({ default: () => null }))

const alimentador = (
  codigo: string,
  dec: number,
  totalUcs: number,
  municipio = 'Recife',
): AlimentadorContinuidade => ({
  alimentador: codigo,
  municipio_principal: municipio,
  total_ucs: totalUcs,
  alimentador_pequeno: totalUcs < 100,
  dec,
  fec: dec / 2,
  dec_sem_dia_critico: dec - 1,
  dec_anterior: dec - 2,
})

// Números redondos inventados. Como na Gold, os maiores DEC são de alimentadores pequenos
let ranking: AlimentadorContinuidade[]

beforeEach(() => {
  ranking = [
    alimentador('ALM-REC-003', 40, 20),
    alimentador('ALM-OLI-001', 30, 50, 'Olinda'),
    alimentador('ALM-REC-001', 15, 2000),
    alimentador('ALM-JAB-001', 10, 900, 'Jaboatão dos Guararapes'),
  ]
})

// Responde como o backend: a série é a do alimentador escolhido ou, sem escolha, a do primeiro do ranking
function responder(endereco: string): ContinuidadeRede {
  const params = new URL(endereco, location.origin).searchParams
  const escolhido = params.get('alimentador')
  const linhas = escolhido ? ranking.filter((linha) => linha.alimentador === escolhido) : ranking
  const mes = (mes_referencia: string) => ({ mes_referencia, dec: 1, fec: 1 })
  return {
    periodo: { inicio: params.get('inicio')!, fim: params.get('fim')! },
    periodo_anterior: { inicio: params.get('inicio_anterior')!, fim: params.get('fim_anterior')! },
    ranking: linhas,
    serie: { alimentador: linhas[0].alimentador, atual: [mes(params.get('fim')!)], anterior: [] },
    ocorrencias: {
      total: 200,
      total_anterior: 100,
      por_causa: params.get('causa')
        ? [{ causa: params.get('causa')!, ocorrencias: 200 }]
        : [
            { causa: 'CLIMATICA', ocorrencias: 120 },
            { causa: 'VEGETACAO', ocorrencias: 80 },
          ],
    },
  }
}

let fetch: MockInstance<typeof globalThis.fetch>

beforeEach(() => {
  fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (entrada) =>
    new Response(JSON.stringify(responder(String(entrada))), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
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
const PERIODO_PADRAO = 'inicio=2025-07&fim=2026-06&inicio_anterior=2024-07&fim_anterior=2025-06'

// O código do alimentador do gráfico aparece acima dele, fora do ranking
const alimentadorDoGrafico = (codigo: string) =>
  screen.findByText(codigo, { selector: 'p' })

test('sem filtro, pede os últimos 12 meses e avisa que DEC e FEC são do alimentador inteiro', async () => {
  abrir()

  expect(await screen.findByText('Piores alimentadores')).toBeInTheDocument()
  await screen.findAllByRole('button', { name: /^ALM-/ })
  expect(enderecos()[0]).toBe(`/api/network/continuity?${PERIODO_PADRAO}`)
  expect(screen.getByRole('note')).toHaveTextContent(/Como ler DEC e FEC\. São sempre do alimentador inteiro/)
  // O ranking tem todos, inclusive os pequenos
  expect(screen.getAllByRole('button', { name: /^ALM-/ })).toHaveLength(4)
  expect(screen.getAllByText('Menos de 100 UCs')).toHaveLength(2)
})

test('o pior DEC e o gráfico pulam os alimentadores com menos de 100 UCs', async () => {
  abrir()

  expect(await screen.findByText('Pior DEC (100 UCs ou mais)')).toBeInTheDocument()
  expect(screen.getByText('15 h')).toBeInTheDocument()
  expect(screen.getByText('ALM-REC-001 · Recife')).toBeInTheDocument()
  // A série da resposta é do ALM-REC-003 (pequeno): o gráfico pede a do ALM-REC-001
  expect(await alimentadorDoGrafico('ALM-REC-001')).toBeInTheDocument()
  expect(enderecos()).toContain(`/api/network/continuity?${PERIODO_PADRAO}&alimentador=ALM-REC-001`)
})

test('se o primeiro do ranking já tem 100 UCs ou mais, não faz a segunda consulta', async () => {
  ranking = ranking.filter((linha) => !linha.alimentador_pequeno)
  abrir()

  expect(await screen.findByText('Pior DEC')).toBeInTheDocument()
  expect(await alimentadorDoGrafico('ALM-REC-001')).toBeInTheDocument()
  expect(enderecos()).toEqual([`/api/network/continuity?${PERIODO_PADRAO}`])
})

test('se todos forem pequenos, o destaque é o pior deles', async () => {
  ranking = ranking.filter((linha) => linha.alimentador_pequeno)
  abrir()

  expect(await screen.findByText('Pior DEC')).toBeInTheDocument()
  expect(screen.getByText('ALM-REC-003 · Recife')).toBeInTheDocument()
  expect(await alimentadorDoGrafico('ALM-REC-003')).toBeInTheDocument()
  expect(enderecos()).toHaveLength(1)
})

test('clicar num alimentador do ranking filtra a tela por ele, mesmo pequeno', async () => {
  abrir()

  fireEvent.click(await screen.findByRole('button', { name: /^ALM-REC-003/ }))

  await waitFor(() =>
    expect(enderecos()).toContain(`/api/network/continuity?${PERIODO_PADRAO}&alimentador=ALM-REC-003`),
  )
  expect(await alimentadorDoGrafico('ALM-REC-003')).toBeInTheDocument()
  expect(screen.getByText('Pior DEC')).toBeInTheDocument()
})

test('a causa filtra só as ocorrências', async () => {
  abrir('/continuidade?base_de=2026-01&base_ate=2026-03&causa=VEGETACAO')

  expect(await screen.findByText('Só vegetação')).toBeInTheDocument()
  expect(enderecos()[0]).toBe(
    '/api/network/continuity?inicio=2026-04&fim=2026-06&inicio_anterior=2026-01&fim_anterior=2026-03&causa=VEGETACAO',
  )
  expect(screen.queryByText('Climática')).not.toBeInTheDocument()
  expect(screen.getAllByRole('button', { name: /^ALM-/ })).toHaveLength(4)
})

test('com várias causas, o bloco das causas aparece ao lado do gráfico', async () => {
  abrir()

  expect(await screen.findByText('Ocorrências por causa')).toBeInTheDocument()
  // No cartão "Principal causa" e na barra
  expect(screen.getAllByText('Climática')).toHaveLength(2)
})

test('com uma causa só, o bloco das causas sai: o cartão "Principal causa" já diz tudo', async () => {
  abrir('/continuidade?causa=VEGETACAO')

  expect(await screen.findByText('Só vegetação')).toBeInTheDocument()
  expect(screen.getByText('Principal causa')).toBeInTheDocument()
  expect(screen.queryByText('Ocorrências por causa')).not.toBeInTheDocument()
})

test('com um alimentador escolhido, o ranking oferece voltar a todos sem subir até os filtros', async () => {
  abrir('/continuidade?alimentador=ALM-REC-001')

  expect(await alimentadorDoGrafico('ALM-REC-001')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /^ALM-/ })).not.toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: 'Ver todos os alimentadores' }))

  await waitFor(() => expect(screen.getAllByRole('button', { name: /^ALM-/ })).toHaveLength(4))
  expect(screen.queryByRole('button', { name: 'Ver todos os alimentadores' })).not.toBeInTheDocument()
})
