import { ErroApi } from '@/lib/api/erro-api'

export const ROTA_LOGIN = '/login'
export const MOTIVO_SESSAO_EXPIRADA = 'sessao-expirada'
// Tela que a pessoa queria abrir; o login leva de volta para ela
export const PARAM_VOLTAR = 'voltar'

// A parte do window.location usada aqui; os testes passam uma versão falsa
type Local = Pick<Location, 'pathname' | 'search' | 'assign'>

// Troca de página recarregando o portal: o que estava na memória vai embora.
// Num objeto para os testes conseguirem observar a chamada
export const navegador = {
  abrir: (endereco: string) => window.location.assign(endereco),
}

// "/login?motivo=sessao-expirada&voltar=%2Freceita". O "/" não precisa de
// voltar: é para lá que o login leva por padrão
export function enderecoDoLogin({ motivo, voltar }: { motivo?: string; voltar?: string } = {}) {
  const params = new URLSearchParams()
  if (motivo) {
    params.set('motivo', motivo)
  }
  if (voltar && voltar !== '/') {
    params.set(PARAM_VOLTAR, voltar)
  }
  const busca = params.toString()
  return busca ? `${ROTA_LOGIN}?${busca}` : ROTA_LOGIN
}

// Só aceita endereços do próprio portal: "//site.com" ou "/\site.com" levariam
// para fora, e voltar para o login não faz sentido
export function destinoDoVoltar(voltar: string | null) {
  if (!voltar || !voltar.startsWith('/') || voltar.startsWith('//') || voltar.startsWith('/\\')) {
    return '/'
  }
  return voltar.startsWith(ROTA_LOGIN) ? '/' : voltar
}

// O JWT dura 15 minutos e não é renovado: um 401 significa que é preciso
// entrar de novo. Recarrega a página de propósito, para limpar o cache
// com dados do usuário que saiu, e guarda a tela para voltar a ela
export function tratarSessaoExpirada(erro: unknown, local: Local = window.location) {
  if (!(erro instanceof ErroApi) || erro.status !== 401) {
    return
  }
  if (local.pathname === ROTA_LOGIN) {
    return
  }

  local.assign(enderecoDoLogin({ motivo: MOTIVO_SESSAO_EXPIRADA, voltar: local.pathname + local.search }))
}
