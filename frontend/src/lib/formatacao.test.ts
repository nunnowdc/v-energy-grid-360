import { expect, test } from 'vitest'
import {
  formatarCompetencia,
  formatarCompetenciaCurta,
  formatarData,
  formatarDataHora,
  formatarEnergia,
  formatarInstante,
  formatarInstanteCurto,
  formatarKwh,
  formatarMoeda,
  formatarMoedaCompacta,
  formatarMoedaCompactaComSinal,
  formatarDiaMes,
  formatarNumero,
  formatarNumeroCompacto,
  formatarPercentualComSinal,
  formatarPeriodo,
  formatarSegundos,
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

test('instante em UTC aparece no horário de Recife, mesmo virando o dia', () => {
  expect(formatarInstante('2026-10-28T21:09:39.757316Z')).toBe('28/10/2026 18:09')
  expect(formatarInstante('2026-10-29T01:30:00Z')).toBe('28/10/2026 22:30')
  expect(formatarInstante('2026-10-28T18:09:00-03:00')).toBe('28/10/2026 18:09')
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

test('contagem compacta, segundos e dia curto', () => {
  expect(semEspacoFixo(formatarNumeroCompacto(780_664))).toBe('780,7 mil')
  expect(semEspacoFixo(formatarNumeroCompacto(1_250_000))).toBe('1,3 mi')
  expect(formatarNumeroCompacto(950)).toBe('950')
  expect(formatarSegundos(19_253)).toBe('19,3 s')
  expect(formatarSegundos(500)).toBe('0,5 s')
  expect(formatarDiaMes('2026-10-27')).toBe('27/10')
})

test('instante curto no horário de Recife, mesmo virando o dia', () => {
  expect(formatarInstanteCurto('2026-11-02T01:10:00Z')).toBe('01/11 22:10')
})
