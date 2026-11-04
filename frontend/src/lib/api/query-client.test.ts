import { expect, test } from 'vitest'
import { ErroApi } from '@/lib/api/erro-api'
import { queryClient } from '@/lib/api/query-client'

const tentarDeNovo = queryClient.getDefaultOptions().queries!.retry as (
  falhas: number,
  erro: unknown,
) => boolean

test('erros 4xx não tentam de novo', () => {
  expect(tentarDeNovo(0, new ErroApi(404, 'x'))).toBe(false)
  expect(tentarDeNovo(0, new ErroApi(429, 'x'))).toBe(false)
})

test('falha de rede e 5xx tentam mais uma vez, e só uma', () => {
  expect(tentarDeNovo(0, new ErroApi(0, 'x'))).toBe(true)
  expect(tentarDeNovo(0, new ErroApi(500, 'x'))).toBe(true)
  expect(tentarDeNovo(1, new ErroApi(500, 'x'))).toBe(false)
})
