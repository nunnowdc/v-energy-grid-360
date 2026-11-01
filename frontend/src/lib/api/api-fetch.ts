import { ErroApi } from '@/lib/api/erro-api'

const PREFIXO_API = '/api'

// Quem precisa de mais tempo (ex.: o agente de IA) passa tempoLimiteMs
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
  tempoLimiteMs?: number
}

export async function apiFetch<T>(caminho: string, opcoes: OpcoesApiFetch = {}): Promise<T> {
  const resposta = await requisitar(caminho, opcoes)

  if (resposta.status === 204) {
    return undefined as T
  }

  return (await resposta.json()) as T
}

// Para rotas que devolvem um arquivo (ex.: a fila em Excel): mesmos erros do
// apiFetch, mas devolve o arquivo e o nome que o backend mandou no Content-Disposition.
// aoProgredir recebe a porcentagem já baixada (0 a 100), só quando a resposta diz o tamanho
export async function apiBaixar(
  caminho: string,
  nomePadrao: string,
  { aoProgredir, ...opcoes }: OpcoesApiFetch & { aoProgredir?: (porcentagem: number) => void } = {},
): Promise<{ arquivo: Blob; nomeArquivo: string }> {
  const resposta = await requisitar(caminho, opcoes)
  const nomeArquivo =
    /filename="([^"]+)"/.exec(resposta.headers.get('Content-Disposition') ?? '')?.[1] ?? nomePadrao
  const total = Number(resposta.headers.get('Content-Length'))

  if (!aoProgredir || !total || !resposta.body) {
    return { arquivo: await resposta.blob(), nomeArquivo }
  }

  const leitor = resposta.body.getReader()
  const partes: Uint8Array<ArrayBuffer>[] = []
  let recebidos = 0
  for (;;) {
    const { done, value } = await leitor.read()
    if (done) {
      break
    }
    partes.push(value)
    recebidos += value.length
    // Com compressão no caminho, o recebido pode passar do Content-Length
    aoProgredir(Math.min(100, Math.round((recebidos / total) * 100)))
  }
  const tipo = resposta.headers.get('Content-Type') ?? ''
  return { arquivo: new Blob(partes, { type: tipo }), nomeArquivo }
}

async function requisitar(
  caminho: string,
  { corpo, headers, signal, tempoLimiteMs = TEMPO_LIMITE_MS, ...opcoes }: OpcoesApiFetch,
): Promise<Response> {
  const sinais = [AbortSignal.timeout(tempoLimiteMs)]
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
    if (temNome(erro, 'TimeoutError')) {
      throw new ErroApi(0, 'O servidor demorou demais para responder. Tente de novo.')
    }
    // Cancelada pelo TanStack Query (ex.: o filtro mudou): não é uma falha
    if (temNome(erro, 'AbortError')) {
      throw erro
    }
    throw new ErroApi(0, 'Não foi possível conectar ao servidor. Verifique se a API está rodando.')
  }

  if (!resposta.ok) {
    throw new ErroApi(resposta.status, await lerMensagemErro(resposta))
  }

  return resposta
}

// Compara pelo nome, e não com instanceof DOMException: o erro de cancelamento
// pode vir de outro contexto (ex.: nos testes) e o instanceof falharia
function temNome(erro: unknown, nome: string) {
  return typeof erro === 'object' && erro !== null && 'name' in erro && erro.name === nome
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
