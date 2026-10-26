import { expect, test } from 'vitest'
import {
  formatarCompetencia,
  formatarMoeda,
  formatarMoedaCompacta,
  formatarNumero,
  formatarPercentualComSinal,
} from '@/lib/formatacao'

// O Intl separa "R$" do número com um espaço que não quebra linha
const semEspacoFixo = (texto: string) => texto.replaceAll(' ', ' ')

test('moeda', () => {
  expect(semEspacoFixo(formatarMoeda(412.5))).toBe('R$ 412,50')
  expect(semEspacoFixo(formatarMoedaCompacta(169_700_000))).toBe('R$ 169,7 mi')
})

test('número', () => {
  expect(formatarNumero(45000)).toBe('45.000')
})

test('percentual com sinal, recebendo pontos (8 = 8%)', () => {
  expect(formatarPercentualComSinal(8)).toBe('+8,0%')
  expect(formatarPercentualComSinal(-6.8)).toBe('-6,8%')
  expect(formatarPercentualComSinal(0)).toBe('0,0%')
})

test('competência', () => {
  expect(formatarCompetencia('2025-07')).toBe('jul/2025')
  expect(formatarCompetencia('2022-12')).toBe('dez/2022')
})
