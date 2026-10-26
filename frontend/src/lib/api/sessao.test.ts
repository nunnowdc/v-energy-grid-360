import { describe, expect, test, vi } from 'vitest'
import { ErroApi } from '@/lib/api/erro-api'
import { tratarSessaoExpirada } from '@/lib/api/sessao'

function localEm(pathname: string) {
  return { pathname, assign: vi.fn() }
}

describe('tratarSessaoExpirada', () => {
  test('401 leva ao login com o aviso de sessão expirada', () => {
    const local = localEm('/receita')
    tratarSessaoExpirada(new ErroApi(401, 'x'), local)
    expect(local.assign).toHaveBeenCalledWith('/login?motivo=sessao-expirada')
  })

  test('outros erros não saem da tela', () => {
    const local = localEm('/receita')
    tratarSessaoExpirada(new ErroApi(403, 'x'), local)
    tratarSessaoExpirada(new ErroApi(500, 'x'), local)
    tratarSessaoExpirada(new TypeError('bug'), local)
    expect(local.assign).not.toHaveBeenCalled()
  })

  test('quem já está no login não é redirecionado de novo', () => {
    const local = localEm('/login')
    tratarSessaoExpirada(new ErroApi(401, 'x'), local)
    expect(local.assign).not.toHaveBeenCalled()
  })
})
