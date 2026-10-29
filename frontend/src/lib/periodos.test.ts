import { describe, expect, test } from 'vitest'
import {
  atalhosDaBase,
  atalhosDoComparado,
  basePadrao,
  baseValida,
  comparadoPadrao,
  comparadoValido,
  mesmosMesesDoAno,
} from '@/lib/periodos'
import { opcoesFiltrosExemplo } from '@/mocks/opcoes-filtros'

// jul/2022 a jun/2026, como a base
const { competencias } = opcoesFiltrosExemplo
const rotulos = (atalhos: { rotulo: string }[]) => atalhos.map(({ rotulo }) => rotulo)

describe('padrões sem escolha', () => {
  test('início da base (Receita) e ano anterior (Indicadores e Continuidade)', () => {
    expect(basePadrao(competencias, 'inicio-da-base')).toEqual({ de: '2022-07', ate: '2023-06' })
    expect(basePadrao(competencias, 'ano-anterior')).toEqual({ de: '2024-07', ate: '2025-06' })
  })
})

describe('base e comparado', () => {
  test('o base tem de 1 a 24 meses e deixa espaço depois dele para um comparado de mesmo tamanho', () => {
    expect(baseValida(competencias, { de: '2022-07', ate: '2024-06' })).toBe(true)
    expect(baseValida(competencias, { de: '2026-05', ate: '2026-05' })).toBe(true)
    expect(baseValida(competencias, { de: '2025-01', ate: '2025-12' })).toBe(false)
    expect(baseValida(competencias, { de: '2026-06', ate: '2026-06' })).toBe(false)
    // 25 meses
    expect(baseValida(competencias, { de: '2022-07', ate: '2024-07' })).toBe(false)
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
