import { screen } from '@testing-library/react'
import { Route, Routes } from 'react-router'
import { afterEach, expect, test, vi } from 'vitest'
import type { IndicadoresGerais, ResumoIndicadores } from '@/hooks/use-indicadores'
import { opcoesFiltrosExemplo } from '@/mocks/opcoes-filtros'
import IndicadoresPage from '@/pages/Indicadores/IndicadoresPage'
import { renderizar } from '@/test/renderizar'

// O gráfico precisa medir a tela, o que o jsdom não faz
vi.mock('@/components/GraficosMensais/GraficosMensais', () => ({ default: () => null }))

const resumo = (periodo: Partial<ResumoIndicadores>): ResumoIndicadores => ({
  inicio: '2026-04',
  fim: '2026-06',
  receita_faturada: 3_000_000,
  consumo_kwh: 4_000_000,
  preco_medio_kwh: 0.75,
  ucs_faturadas: 1000,
  faturas: 3000,
  faturas_atrasadas: 60,
  ...periodo,
})

// Números redondos inventados para conferir as contas da tela
const indicadores: IndicadoresGerais = {
  atual: resumo({ receita_faturada: 3_300_000, faturas_atrasadas: 90 }),
  anterior: resumo({ inicio: '2026-01', fim: '2026-03' }),
  mensal: { atual: [], anterior: [] },
  por_classe: [
    { classe: 'COMERCIAL', receita_faturada: 1_100_000, receita_faturada_anterior: 1_000_000 },
    { classe: 'RESIDENCIAL', receita_faturada: 2_200_000, receita_faturada_anterior: 2_000_000 },
  ],
}

function abrir(url: string) {
  return renderizar(
    <Routes>
      <Route path="/" element={<IndicadoresPage />} />
    </Routes>,
    { url, opcoesFiltros: opcoesFiltrosExemplo },
  )
}

function responderCom(corpo: unknown) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(corpo), { status: 200, headers: { 'Content-Type': 'application/json' } }),
  )
}

afterEach(() => {
  vi.restoreAllMocks()
})

test('sem filtro, pede o último ano da base contra o anterior', async () => {
  const fetch = responderCom(indicadores)
  abrir('/')

  await screen.findByText('Receita faturada')
  expect(fetch.mock.calls[0][0]).toBe('/api/metrics/general?inicio=2025-07&fim=2026-06&inicio_anterior=2024-07&fim_anterior=2025-06')
})

test('manda os períodos, o município e a classe escolhidos', async () => {
  const fetch = responderCom(indicadores)
  // Base jan–mar/2026: não cabem os mesmos meses depois, então o comparado são os últimos 3 meses
  abrir('/?base_de=2026-01&base_ate=2026-03&municipio=Recife&classe=RURAL')

  await screen.findByText('Receita faturada')
  expect(fetch.mock.calls[0][0]).toBe(
    '/api/metrics/general?inicio=2026-04&fim=2026-06&inicio_anterior=2026-01&fim_anterior=2026-03&municipio=Recife&classe=RURAL',
  )
})

test('base escolhido leva o comparado para os mesmos meses do ano mais recente', async () => {
  const fetch = responderCom(indicadores)
  abrir('/?base_de=2024-10&base_ate=2024-12')

  await screen.findByText('Receita faturada')
  expect(fetch.mock.calls[0][0]).toBe(
    '/api/metrics/general?inicio=2025-10&fim=2025-12&inicio_anterior=2024-10&fim_anterior=2024-12',
  )
})

test('base sem espaço para o comparado volta ao padrão', async () => {
  const fetch = responderCom(indicadores)
  // Depois de 2025 inteiro não cabem mais 12 meses na base
  abrir('/?base_de=2025-01&base_ate=2025-12')

  await screen.findByText('Receita faturada')
  expect(fetch.mock.calls[0][0]).toBe('/api/metrics/general?inicio=2025-07&fim=2026-06&inicio_anterior=2024-07&fim_anterior=2025-06')
})

test('mostra os KPIs com a variação contra o período anterior', async () => {
  responderCom(indicadores)
  abrir('/?base_de=2026-01&base_ate=2026-03')

  // Espera os dados: o botão do período já mostra "abr/2026 – jun/2026" antes deles
  expect(await screen.findByText(/comparado com jan\/2026 – mar\/2026/)).toBeInTheDocument()
  expect(screen.getAllByText('abr/2026 – jun/2026')).toHaveLength(2)
  // jan–mar contra abr–jun: meses diferentes do ano
  expect(screen.getByText(/meses diferentes do ano/)).toBeInTheDocument()
  // Receita: 3,3 mi contra 3 mi = +10%
  expect(screen.getAllByText('+10,0%')).not.toHaveLength(0)
  // Atraso: 90 de 3.000 faturas, contra 60 antes = +50%
  expect(screen.getByText('3% das faturas do período')).toBeInTheDocument()
  expect(screen.getByText('+50,0%')).toBeInTheDocument()
  expect(screen.getByText('Em jun/2026')).toBeInTheDocument()
})

test('as classes aparecem da maior receita para a menor', async () => {
  responderCom(indicadores)
  abrir('/')

  await screen.findByText('Residencial')
  const nomes = screen.getAllByText(/^(Residencial|Comercial)$/).map((item) => item.textContent)
  expect(nomes).toEqual(['Residencial', 'Comercial'])
})

test('sem faturas no recorte, avisa em vez de mostrar zeros', async () => {
  responderCom({ ...indicadores, atual: resumo({ faturas: 0 }) })
  abrir('/?classe=RURAL')

  expect(await screen.findAllByText('Nenhuma fatura para esses filtros.')).toHaveLength(3)
})
