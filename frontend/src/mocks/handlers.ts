import { delay, http, HttpResponse } from 'msw'
import type { MudancaOrdem } from '@/hooks/use-ordens-inspecao'
import { gerarIndicadores } from '@/mocks/indicadores'
import { buscarFila, gerarOrdens, listarOrdens, mudarOrdem } from '@/mocks/inspecoes'
import { opcoesAtuais } from '@/mocks/opcoes-atuais'
import { gerarReceita } from '@/mocks/receita'

// Simula a demora da rede para dar para ver o carregamento (nos testes, sem demora)
const demora = (ms: number) => delay(import.meta.env.MODE === 'test' ? 0 : ms)

// Respostas de exemplo para as rotas que o backend ainda não tem.
// Quando a rota real existir, apague o handler dela daqui
export const handlers = [
  http.get('/api/metrics/general', async ({ request }) => {
    const params = new URL(request.url).searchParams
    await demora(600)
    const indicadores = gerarIndicadores(
      await opcoesAtuais(),
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
    await demora(600)
    return HttpResponse.json(
      gerarReceita(await opcoesAtuais(), params.get('municipio'), params.get('bairro'), params.get('classe')),
    )
  }),

  http.get('/api/inspections/queue', async ({ request }) => {
    const params = new URL(request.url).searchParams
    await demora(500)
    const filtros = { municipio: params.get('municipio'), bairro: params.get('bairro'), classe: params.get('classe') }
    return HttpResponse.json(
      buscarFila(await opcoesAtuais(), filtros, Number(params.get('pagina') ?? 1), Number(params.get('limite') ?? 20)),
    )
  }),

  http.get('/api/inspections/orders', async () => {
    await demora(300)
    return HttpResponse.json({ itens: listarOrdens() })
  }),

  http.post('/api/inspections/order', async ({ request }) => {
    const { ids_uc } = (await request.json()) as { ids_uc: string[] }
    await demora(500)
    return HttpResponse.json({ ordens: gerarOrdens(await opcoesAtuais(), ids_uc) }, { status: 201 })
  }),

  http.patch('/api/inspections/:idOrdem', async ({ params, request }) => {
    const mudanca = (await request.json()) as MudancaOrdem
    await demora(400)
    const resultado = mudarOrdem(String(params.idOrdem), mudanca)
    return 'erro' in resultado
      ? HttpResponse.json({ detail: resultado.erro }, { status: resultado.status })
      : HttpResponse.json(resultado.ordem)
  }),

  http.delete('/api/inspections/:idOrdem', async ({ params }) => {
    await demora(400)
    const resultado = mudarOrdem(String(params.idOrdem), { status: 'CANCELADA' })
    return 'erro' in resultado
      ? HttpResponse.json({ detail: resultado.erro }, { status: resultado.status })
      : HttpResponse.json(resultado.ordem)
  }),
]
