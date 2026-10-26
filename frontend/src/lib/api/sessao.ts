import { ErroApi } from '@/lib/api/erro-api'

export const ROTA_LOGIN = '/login'
export const MOTIVO_SESSAO_EXPIRADA = 'sessao-expirada'

// A parte do window.location usada aqui; os testes passam uma versão falsa
type Local = Pick<Location, 'pathname' | 'assign'>

// O JWT dura 15 minutos e não é renovado: um 401 significa que é preciso
// entrar de novo. Recarrega a página de propósito, para limpar o cache
// com dados do usuário que saiu
export function tratarSessaoExpirada(erro: unknown, local: Local = window.location) {
  if (!(erro instanceof ErroApi) || erro.status !== 401) {
    return
  }
  if (local.pathname === ROTA_LOGIN) {
    return
  }

  local.assign(`${ROTA_LOGIN}?motivo=${MOTIVO_SESSAO_EXPIRADA}`)
}
