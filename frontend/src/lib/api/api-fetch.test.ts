import { afterEach, describe, expect, test, vi } from 'vitest'
import { apiFetch } from '@/lib/api/api-fetch'
import { ErroApi } from '@/lib/api/erro-api'

// Troca o fetch do navegador por uma resposta pronta
function responder(status: number, corpo?: unknown) {
  const texto = corpo === undefined ? null : typeof corpo === 'string' ? corpo : JSON.stringify(corpo)
  const fetchFalso = vi.fn().mockResolvedValue(new Response(texto, { status }))
  vi.stubGlobal('fetch', fetchFalso)
  return fetchFalso
}

async function erroDe(promessa: Promise<unknown>) {
  try {
    await promessa
  } catch (erro) {
    return erro as ErroApi
  }
  throw new Error('A chamada deveria ter falhado')
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('sucesso', () => {
  test('coloca o prefixo /api, envia o cookie e devolve o JSON', async () => {
    const fetchFalso = responder(200, { valor: 42 })
    expect(await apiFetch('/metrics/general')).toEqual({ valor: 42 })
    const [url, opcoes] = fetchFalso.mock.calls[0]
    expect(url).toBe('/api/metrics/general')
    expect(opcoes.credentials).toBe('same-origin')
  })

  test('envia o corpo como JSON', async () => {
    const fetchFalso = responder(200, {})
    await apiFetch('/inspections/order', { method: 'POST', corpo: { idUc: 'UC129001' } })
    const [, opcoes] = fetchFalso.mock.calls[0]
    expect(opcoes.body).toBe('{"idUc":"UC129001"}')
    expect(opcoes.headers['Content-Type']).toBe('application/json')
  })

  test('204 devolve undefined', async () => {
    responder(204)
    expect(await apiFetch('/vazio')).toBeUndefined()
  })
})

describe('erros com mensagem pronta para a tela', () => {
  test('usa o texto do backend quando ele existe', async () => {
    responder(404, { detail: 'Unidade consumidora UC999999 não encontrada' })
    const erro = await erroDe(apiFetch('/uc/UC999999/360'))
    expect(erro).toBeInstanceOf(ErroApi)
    expect(erro.status).toBe(404)
    expect(erro.message).toBe('Unidade consumidora UC999999 não encontrada')
  })

  test.each([
    [401, 'Sua sessão expirou. Entre novamente.'],
    [403, 'Você não tem permissão para acessar estes dados.'],
    [429, 'Muitas tentativas. Aguarde um instante e tente de novo.'],
  ])('%i usa sempre a mensagem do portal, mesmo com texto do backend', async (status, mensagem) => {
    responder(status, { detail: 'Not authenticated' })
    expect((await erroDe(apiFetch('/x'))).message).toBe(mensagem)
  })

  test('422 com lista de erros usa a mensagem padrão', async () => {
    responder(422, { detail: [{ msg: 'field required' }] })
    expect((await erroDe(apiFetch('/x'))).message).toBe('Os dados enviados são inválidos.')
  })

  test('500 sem JSON usa a mensagem genérica', async () => {
    responder(500, 'Internal Server Error')
    expect((await erroDe(apiFetch('/x'))).message).toBe(
      'Algo deu errado no servidor. Tente de novo em instantes.',
    )
  })
})

describe('quando a resposta nem chega', () => {
  test('servidor fora do ar vira ErroApi com status 0', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    const erro = await erroDe(apiFetch('/x'))
    expect(erro.status).toBe(0)
    expect(erro.message).toContain('Não foi possível conectar ao servidor')
  })

  test('demora demais vira ErroApi com status 0', async () => {
    // Tempo limite de verdade, mas de 10 ms em vez de 30 s
    const timeoutOriginal = AbortSignal.timeout.bind(AbortSignal)
    vi.spyOn(AbortSignal, 'timeout').mockImplementation(() => timeoutOriginal(10))
    // Servidor que nunca responde: só termina quando o sinal cancela
    vi.stubGlobal(
      'fetch',
      (_url: string, opcoes: RequestInit) =>
        new Promise((_ok, falhar) => {
          opcoes.signal!.addEventListener('abort', () => falhar(opcoes.signal!.reason))
        }),
    )
    const erro = await erroDe(apiFetch('/x'))
    expect(erro.status).toBe(0)
    expect(erro.message).toContain('demorou demais')
  })

  test('busca cancelada (o filtro mudou) não vira ErroApi', async () => {
    vi.stubGlobal('fetch', (_url: string, opcoes: RequestInit) => Promise.reject(opcoes.signal!.reason))
    const controle = new AbortController()
    controle.abort()
    const erro = await erroDe(apiFetch('/x', { signal: controle.signal }))
    expect(erro).not.toBeInstanceOf(ErroApi)
    expect((erro as Error).name).toBe('AbortError')
  })
})
