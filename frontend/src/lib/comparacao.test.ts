import { expect, test } from 'vitest'
import { tomDaVariacao, variacaoPercentual } from '@/lib/comparacao'

test('variação em pontos percentuais', () => {
  expect(variacaoPercentual(108, 100)).toBeCloseTo(8)
  expect(variacaoPercentual(90, 100)).toBeCloseTo(-10)
})

test('sem valor anterior, não há variação', () => {
  expect(variacaoPercentual(50, 0)).toBeUndefined()
})

test.each([
  [8, 'subir-e-bom', 'positivo'],
  [-8, 'subir-e-bom', 'negativo'],
  [8, 'subir-e-ruim', 'negativo'],
  [-8, 'subir-e-ruim', 'positivo'],
  [0, 'subir-e-bom', 'neutro'],
  [8, undefined, 'neutro'],
] as const)('variação %d com sentido %s é %s', (variacao, sentido, tom) => {
  expect(tomDaVariacao(variacao, sentido)).toBe(tom)
})
