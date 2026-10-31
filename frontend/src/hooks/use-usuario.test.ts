import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { afterEach, expect, test, vi } from 'vitest'
import { useSair, useSessao } from '@/hooks/use-usuario'
import { navegador } from '@/lib/api/sessao'
import { usuarioApiExemplo } from '@/mocks/usuarios'

function responder(status: number, corpo?: unknown) {
  return vi
    .spyOn(globalThis, 'fetch')
    .mockResolvedValue(new Response(corpo === undefined ? null : JSON.stringify(corpo), { status }))
}

function comCache<T>(hook: () => T) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const envolver = ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
  return renderHook(hook, { wrapper: envolver })
}

afterEach(() => {
  vi.restoreAllMocks()
})

test('a sessão vem do /auth/me, com as permissões do perfil', async () => {
  const fetch = responder(200, usuarioApiExemplo('OPERACAO'))
  const { result } = comCache(useSessao)

  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(fetch.mock.calls[0][0]).toBe('/api/auth/me')
  expect(result.current.data).toMatchObject({ perfil: 'OPERACAO', permissoes: ['ver_continuidade', 'usar_agente_ia'] })
})

test('401 no /auth/me é visitante sem login, e não erro', async () => {
  responder(401, { detail: 'Não autenticado' })
  const { result } = comCache(useSessao)

  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(result.current.data).toBeNull()
})

test('perfil que o portal não conhece vira erro, sem nenhuma tela liberada', async () => {
  responder(200, { ...usuarioApiExemplo(), perfil: 'ESTAGIARIO' })
  const { result } = comCache(useSessao)

  await waitFor(() => expect(result.current.isError).toBe(true))
  expect(result.current.error?.message).toMatch(/perfil não é reconhecido/)
})

test('sair chama o logout e recarrega no login, mesmo com a sessão já vencida', async () => {
  const abrir = vi.spyOn(navegador, 'abrir').mockImplementation(() => {})
  const fetch = responder(401, { detail: 'Não autenticado' })
  const { result } = comCache(useSair)

  result.current.mutate()

  await waitFor(() => expect(abrir).toHaveBeenCalledWith('/login'))
  expect(fetch.mock.calls[0][0]).toBe('/api/auth/logout')
  expect(fetch.mock.calls[0][1]?.method).toBe('POST')
})
