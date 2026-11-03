import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, test, vi } from 'vitest'
import InsightIa from '@/components/InsightIa/InsightIa'
import type { InsightIa as Insight } from '@/hooks/use-insight-ia'
import { renderizar } from '@/test/renderizar'

const json = (corpo: unknown, status = 200) =>
  new Response(JSON.stringify(corpo), { status, headers: { 'Content-Type': 'application/json' } })

const insight = (campos: Partial<Insight> = {}): Insight => ({
  tela: 'visao_360_uc',
  entidade_id: 'UC000001',
  insight_texto: 'O consumo caiu 34% de maio para junho de 2026 (309 kWh para 203 kWh).',
  metricas_destaque: { competencia: '2026-06-01', consumo_kwh: 203 },
  selo: 'auditado_llm',
  tempo_ms: 0,
  ...campos,
})

function abrir() {
  return renderizar(<InsightIa tela="visao_360_uc" entidadeId="UC000001" descricao="Sobre esta unidade consumidora" />)
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('insight da IA', () => {
  test('busca o insight da UC e mostra o texto com o selo de números conferidos', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(json(insight()))
    abrir()

    expect(screen.getByText('Insight da IA')).toBeInTheDocument()
    expect(screen.getByText('A IA está analisando os dados…')).toBeInTheDocument()

    expect(await screen.findByText(/O consumo caiu 34%/)).toBeInTheDocument()
    expect(fetch.mock.calls[0][0]).toBe('/api/ai/insights/visao_360_uc/UC000001')
    expect(screen.getByText('Números conferidos')).toBeInTheDocument()
    expect(screen.getByText(/Gerado por IA a partir da base Gold/)).toBeInTheDocument()
    expect(screen.queryByText(/^Fonte:/)).not.toBeInTheDocument()
  })

  test('mostra as tabelas de origem quando a resposta traz', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json(insight({ fontes: ['fact_faturamento'] })))
    abrir()
    expect(await screen.findByText('Fonte: fact_faturamento')).toBeInTheDocument()
  })

  test('texto que não passou na conferência dos números leva o selo de sem conferência', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      json(
        insight({
          selo: 'template_fallback',
          insight_texto: 'Não foi possível validar numericamente o texto gerado; consulte os dados exibidos.',
        }),
      ),
    )
    abrir()
    expect(await screen.findByText('Sem conferência')).toBeInTheDocument()
    expect(screen.queryByText('Números conferidos')).not.toBeInTheDocument()
  })

  test('perfil sem acesso ao insight não vê a caixa', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ detail: 'Sem permissão' }, 403))
    abrir()
    await waitFor(() => expect(screen.queryByText('Insight da IA')).not.toBeInTheDocument())
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  test('erro no servidor fica dentro da caixa e não tenta de novo sozinho', async () => {
    const fetch = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(json({ detail: 'Erro ao gerar insight.' }, 500))
      .mockResolvedValueOnce(json(insight()))
    abrir()

    expect(await screen.findByText('Erro ao gerar insight.')).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }))
    expect(await screen.findByText(/O consumo caiu 34%/)).toBeInTheDocument()
  })
})
