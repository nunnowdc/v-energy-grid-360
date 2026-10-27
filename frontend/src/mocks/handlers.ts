import { delay, http, HttpResponse } from 'msw'
import { gerarIndicadores } from '@/mocks/indicadores'
import { opcoesFiltrosExemplo } from '@/mocks/opcoes-filtros'
import { gerarReceita } from '@/mocks/receita'

// Respostas de exemplo para as rotas que o backend ainda não tem.
// Quando a rota real existir, apague o handler dela daqui
export const handlers = [
  http.get('/api/filters/options', async () => {
    // Simula a demora da rede para dar para ver o carregamento
    await delay(400)
    return HttpResponse.json(opcoesFiltrosExemplo)
  }),

  http.get('/api/metrics/general', async ({ request }) => {
    const params = new URL(request.url).searchParams
    await delay(600)
    const indicadores = gerarIndicadores(
      params.get('inicio'),
      params.get('fim'),
      params.get('municipio'),
      params.get('classe'),
    )
    if (!indicadores) {
      return HttpResponse.json({ detail: 'Use os últimos 3, 6 ou 12 meses da base.' }, { status: 422 })
    }
    return HttpResponse.json(indicadores)
  }),

  http.get('/api/metrics/revenue-variance', async ({ request }) => {
    const params = new URL(request.url).searchParams
    await delay(600)
    return HttpResponse.json(gerarReceita(params.get('municipio'), params.get('bairro'), params.get('classe')))
  }),
]
