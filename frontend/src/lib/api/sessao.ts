import { ErroApi } from '@/lib/api/erro-api'

export const ROTA_LOGIN = '/login'
export const MOTIVO_SESSAO_EXPIRADA = 'sessao-expirada'

// O JWT dura 15 minutos e não é renovado: um 401 significa que é preciso
// entrar de novo. Recarrega a página de propósito, para limpar o cache
// com dados do usuário que saiu
export function tratarSessaoExpirada(erro: unknown) {
  if (!(erro instanceof ErroApi) || erro.status !== 401) {
    return
  }
  if (window.location.pathname === ROTA_LOGIN) {
    return
  }

  window.location.assign(`${ROTA_LOGIN}?motivo=${MOTIVO_SESSAO_EXPIRADA}`)
}
