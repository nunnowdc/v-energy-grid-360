import { ErroApi } from '@/lib/api/erro-api'

const PREFIXO_API = '/api'

// O agente de IA pode levar alguns segundos para responder
const TEMPO_LIMITE_MS = 30_000

const MENSAGEM_GENERICA = 'Algo deu errado no servidor. Tente de novo em instantes.'

const mensagensPorStatus: Record<number, string> = {
  401: 'Sua sessão expirou. Entre novamente.',
  403: 'Você não tem permissão para acessar estes dados.',
  404: 'Não encontramos o que você procurou.',
  422: 'Os dados enviados são inválidos.',
  429: 'Muitas tentativas. Aguarde um instante e tente de novo.',
}

// Nestes status a mensagem é sempre a do portal (o texto padrão do backend
// vem em inglês); nos demais, o texto do backend tem prioridade quando existe
const statusComMensagemFixa = [401, 403, 429]

type OpcoesApiFetch = Omit<RequestInit, 'body' | 'headers'> & {
  corpo?: unknown
  headers?: Record<string, string>
}

export async function apiFetch<T>(
  caminho: string,
  { corpo, headers, signal, ...opcoes }: OpcoesApiFetch = {},
): Promise<T> {
  const sinais = [AbortSignal.timeout(TEMPO_LIMITE_MS)]
  if (signal) {
    sinais.push(signal)
  }

  let resposta: Response
  try {
    resposta = await fetch(`${PREFIXO_API}${caminho}`, {
      ...opcoes,
      // Envia o cookie de login; o proxy do Vite deixa front e API no mesmo endereço
      credentials: 'same-origin',
      headers: {
        Accept: 'application/json',
        ...(corpo !== undefined && { 'Content-Type': 'application/json' }),
        ...headers,
      },
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
      signal: AbortSignal.any(sinais),
    })
  } catch (erro) {
    if (erro instanceof DOMException && erro.name === 'TimeoutError') {
      throw new ErroApi(0, 'O servidor demorou demais para responder. Tente de novo.')
    }
    // Cancelada pelo TanStack Query (ex.: o filtro mudou): não é uma falha
    if (erro instanceof DOMException && erro.name === 'AbortError') {
      throw erro
    }
    throw new ErroApi(0, 'Não foi possível conectar ao servidor. Verifique se a API está rodando.')
  }

  if (!resposta.ok) {
    throw new ErroApi(resposta.status, await lerMensagemErro(resposta))
  }

  if (resposta.status === 204) {
    return undefined as T
  }

  return (await resposta.json()) as T
}

// O FastAPI responde { "detail": "texto" } nos erros que o próprio código levanta
async function lerMensagemErro(resposta: Response) {
  const padrao = mensagensPorStatus[resposta.status] ?? MENSAGEM_GENERICA

  if (statusComMensagemFixa.includes(resposta.status)) {
    return padrao
  }

  try {
    const { detail } = await resposta.json()
    if (typeof detail === 'string') {
      return detail
    }
  } catch {
    // Corpo vazio ou que não é JSON: fica a mensagem padrão
  }

  return padrao
}
