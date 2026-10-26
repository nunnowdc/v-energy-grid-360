import { renderHook } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

// O perfil de teste é lido do .env quando o módulo carrega,
// então cada caso recarrega o módulo com outro valor
async function usuarioCom(valor: string | undefined) {
  vi.resetModules()
  vi.stubEnv('VITE_PERFIL_TESTE', valor)
  const { useUsuario } = await import('@/hooks/use-usuario')
  return renderHook(() => useUsuario()).result.current
}

afterEach(() => {
  vi.unstubAllEnvs()
})

test('aceita o perfil em maiúsculas ou minúsculas', async () => {
  expect((await usuarioCom('DIRETORIA')).usuario.perfil).toBe('DIRETORIA')
  expect((await usuarioCom('atendimento')).usuario.perfil).toBe('ATENDIMENTO')
})

test('valor inválido ou ausente vira ADMIN_TI', async () => {
  expect((await usuarioCom('inventado')).usuario.perfil).toBe('ADMIN_TI')
  expect((await usuarioCom(undefined)).usuario.perfil).toBe('ADMIN_TI')
})

test('pode() responde pelas permissões do perfil', async () => {
  const { pode } = await usuarioCom('OPERACAO')
  expect(pode('ver_continuidade')).toBe(true)
  expect(pode('ver_receita')).toBe(false)
})
