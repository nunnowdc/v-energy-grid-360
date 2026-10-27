import { expect, test } from 'vitest'
import {
  formatarCompetencia,
  formatarCompetenciaCurta,
  formatarData,
  formatarDataHora,
  formatarKwh,
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

test('datas sem depender do fuso do computador', () => {
  expect(formatarData('2026-06-21')).toBe('21/06/2026')
  expect(formatarDataHora('2026-06-12T05:49:00')).toBe('12/06/2026 05:49')
})

test('kWh e competência curta', () => {
  expect(formatarKwh(1203.5)).toBe('1.203,5 kWh')
  expect(formatarCompetenciaCurta('2025-07')).toBe('jul/25')
})
