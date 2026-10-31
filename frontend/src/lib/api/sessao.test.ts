import { describe, expect, test, vi } from 'vitest'
import { ErroApi } from '@/lib/api/erro-api'
import { destinoDoVoltar, enderecoDoLogin, tratarSessaoExpirada } from '@/lib/api/sessao'

function localEm(pathname: string, search = '') {
  return { pathname, search, assign: vi.fn() }
}

describe('tratarSessaoExpirada', () => {
  test('401 leva ao login com o aviso de sessão expirada e a tela para voltar', () => {
    const local = localEm('/receita', '?municipio=Recife')
    tratarSessaoExpirada(new ErroApi(401, 'x'), local)
    expect(local.assign).toHaveBeenCalledWith(
      '/login?motivo=sessao-expirada&voltar=%2Freceita%3Fmunicipio%3DRecife',
    )
  })

  test('no "/" não precisa guardar a tela', () => {
    const local = localEm('/')
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

test('enderecoDoLogin monta o motivo e a tela para voltar', () => {
  expect(enderecoDoLogin()).toBe('/login')
  expect(enderecoDoLogin({ voltar: '/' })).toBe('/login')
  expect(enderecoDoLogin({ voltar: '/inspecoes' })).toBe('/login?voltar=%2Finspecoes')
})

test('destinoDoVoltar só aceita telas do próprio portal', () => {
  expect(destinoDoVoltar('/continuidade?alimentador=ALM-REC-001')).toBe('/continuidade?alimentador=ALM-REC-001')
  expect(destinoDoVoltar(null)).toBe('/')
  expect(destinoDoVoltar('https://site.com')).toBe('/')
  expect(destinoDoVoltar('//site.com')).toBe('/')
  expect(destinoDoVoltar('/\\site.com')).toBe('/')
  expect(destinoDoVoltar('/login?motivo=sessao-expirada')).toBe('/')
})
