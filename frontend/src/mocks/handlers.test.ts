import { getResponse } from 'msw'
import { expect, test } from 'vitest'
import { handlers } from '@/mocks/handlers'

test('o exemplo de /api/filters/options cobre os 48 meses da base', async () => {
  const requisicao = new Request(new URL('/api/filters/options', location.origin))
  const resposta = await getResponse(handlers, requisicao)
  const corpo = await resposta!.json()

  expect(corpo.competencias).toHaveLength(48)
  expect(corpo.competencias[0]).toBe('2022-07')
  expect(corpo.competencias.at(-1)).toBe('2026-06')
})
