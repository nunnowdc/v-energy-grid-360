import { expect, test } from 'vitest'
import {
  formatarCompetencia,
  formatarCompetenciaCurta,
  formatarData,
  formatarDataHora,
  formatarEnergia,
  formatarKwh,
  formatarMoeda,
  formatarMoedaCompacta,
  formatarMoedaCompactaComSinal,
  formatarNumero,
  formatarPercentualComSinal,
  formatarPeriodo,
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

test('energia na unidade que deixa o número curto', () => {
  expect(formatarEnergia(19_450_000)).toBe('19,5 GWh')
  expect(formatarEnergia(812_300)).toBe('812,3 MWh')
  expect(formatarEnergia(203)).toBe('203 kWh')
})

test('período entre duas competências', () => {
  expect(formatarPeriodo('2025-07', '2026-06')).toBe('jul/2025 – jun/2026')
})

test('diferença em reais sempre com sinal', () => {
  expect(semEspacoFixo(formatarMoedaCompactaComSinal(22_500_000))).toBe('+R$ 22,5 mi')
  expect(semEspacoFixo(formatarMoedaCompactaComSinal(-4_100_000))).toBe('-R$ 4,1 mi')
})
