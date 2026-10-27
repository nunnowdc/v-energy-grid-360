import { expect, test } from 'vitest'
import { variacaoPercentual } from '@/lib/comparacao'

test('variação em pontos percentuais', () => {
  expect(variacaoPercentual(108, 100)).toBeCloseTo(8)
  expect(variacaoPercentual(90, 100)).toBeCloseTo(-10)
})

test('sem valor anterior, não há variação', () => {
  expect(variacaoPercentual(50, 0)).toBeUndefined()
})
