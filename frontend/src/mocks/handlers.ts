import { delay, http, HttpResponse } from 'msw'
import { opcoesFiltrosExemplo } from '@/mocks/opcoes-filtros'

// Respostas de exemplo para as rotas que o backend ainda não tem.
// Quando a rota real existir, apague o handler dela daqui
export const handlers = [
  http.get('/api/filters/options', async () => {
    // Simula a demora da rede para dar para ver o carregamento
    await delay(400)
    return HttpResponse.json(opcoesFiltrosExemplo)
  }),
]
