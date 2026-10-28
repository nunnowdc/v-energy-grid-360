import { delay, http, HttpResponse } from 'msw'
import { gerarContinuidade } from '@/mocks/continuidade'
import { opcoesAtuais } from '@/mocks/opcoes-atuais'

// Simula a demora da rede para dar para ver o carregamento (nos testes, sem demora)
const demora = (ms: number) => delay(import.meta.env.MODE === 'test' ? 0 : ms)

// Respostas de exemplo para as rotas que o backend ainda não tem.
// Quando a rota real existir, apague o handler dela daqui
export const handlers = [
  http.get('/api/network/continuity', async ({ request }) => {
    const params = new URL(request.url).searchParams
    await demora(600)
    const continuidade = gerarContinuidade(
      await opcoesAtuais(),
      params.get('inicio'),
      params.get('fim'),
      params.get('municipio'),
      params.get('alimentador'),
      params.get('causa'),
    )
    if (!continuidade) {
      return HttpResponse.json({ detail: 'Use os últimos 3, 6 ou 12 meses da base.' }, { status: 422 })
    }
    return HttpResponse.json(continuidade)
  }),
]
