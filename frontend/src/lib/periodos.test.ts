import { describe, expect, test } from 'vitest'
import {
  atalhosDaBase,
  atalhosDoComparado,
  atalhosDoPeriodo,
  baseValida,
  comparadoPadrao,
  comparadoValido,
  mesmosMesesDoAno,
  periodoComAnterior,
} from '@/lib/periodos'
import { opcoesFiltrosExemplo } from '@/mocks/opcoes-filtros'

// jul/2022 a jun/2026, como a base
const { competencias } = opcoesFiltrosExemplo
const rotulos = (atalhos: { rotulo: string }[]) => atalhos.map(({ rotulo }) => rotulo)

describe('Indicadores e Continuidade', () => {
  test('o período vale de 1 a 24 meses, com o anterior inteiro dentro da base', () => {
    expect(periodoComAnterior(competencias, { de: '2026-06', ate: '2026-06' })).toBe(true)
    expect(periodoComAnterior(competencias, { de: '2024-07', ate: '2026-06' })).toBe(true)
    // 25 meses
    expect(periodoComAnterior(competencias, { de: '2024-06', ate: '2026-06' })).toBe(false)
    // O ano anterior a 2023 não está na base
    expect(periodoComAnterior(competencias, { de: '2023-01', ate: '2023-12' })).toBe(false)
    // Fora da base ou invertido
    expect(periodoComAnterior(competencias, { de: '2026-06', ate: '2026-07' })).toBe(false)
    expect(periodoComAnterior(competencias, { de: '2025-06', ate: '2025-01' })).toBe(false)
  })

  test('atalhos: últimos meses e anos civis que têm o ano anterior na base', () => {
    expect(rotulos(atalhosDoPeriodo(competencias))).toEqual([
      'Últimos 3 meses',
      'Últimos 6 meses',
      'Últimos 12 meses',
      'Últimos 24 meses',
      'Ano de 2024',
      'Ano de 2025',
    ])
  })
})

describe('Receita', () => {
  test('o base precisa deixar espaço depois dele para um comparado de mesmo tamanho', () => {
    expect(baseValida(competencias, { de: '2022-07', ate: '2024-06' })).toBe(true)
    expect(baseValida(competencias, { de: '2025-01', ate: '2025-12' })).toBe(false)
  })

  test('o comparado começa depois do fim do base e cabe na base', () => {
    const base = { de: '2023-01', ate: '2023-03' }
    expect(comparadoValido(competencias, base, '2023-04')).toBe(true)
    expect(comparadoValido(competencias, base, '2026-04')).toBe(true)
    expect(comparadoValido(competencias, base, '2023-03')).toBe(false)
    expect(comparadoValido(competencias, base, '2026-05')).toBe(false)
  })

  test('comparado padrão: os mesmos meses no ano mais recente que cabe', () => {
    expect(comparadoPadrao(competencias, { de: '2023-01', ate: '2023-03' })).toEqual({ de: '2026-01', ate: '2026-03' })
    // 13 meses a partir de mar/2024: os mesmos meses não cabem mais, vão os últimos 13 meses
    expect(comparadoPadrao(competencias, { de: '2024-03', ate: '2025-03' })).toEqual({ de: '2025-06', ate: '2026-06' })
  })

  test('atalhos do base: anos jul–jun e anos civis que deixam espaço para o comparado', () => {
    expect(rotulos(atalhosDaBase(competencias))).toEqual([
      'jul/2022 – jun/2023',
      'jul/2023 – jun/2024',
      'jul/2024 – jun/2025',
      'Ano de 2023',
      'Ano de 2024',
    ])
  })

  test('atalhos do comparado: os mesmos meses do ano, nos anos seguintes', () => {
    expect(rotulos(atalhosDoComparado(competencias, { de: '2023-01', ate: '2023-03' }))).toEqual([
      'jan/2024 – mar/2024',
      'jan/2025 – mar/2025',
      'jan/2026 – mar/2026',
    ])
  })

  test('mesmos meses do ano dos dois lados', () => {
    expect(mesmosMesesDoAno({ de: '2023-01', ate: '2023-03' }, { de: '2026-01', ate: '2026-03' })).toBe(true)
    expect(mesmosMesesDoAno({ de: '2023-01', ate: '2023-03' }, { de: '2025-07', ate: '2025-09' })).toBe(false)
  })
})
