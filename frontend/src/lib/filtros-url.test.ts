import { describe, expect, test } from 'vitest'
import {
  aplicarFiltro,
  aplicarFiltros,
  lerFiltros,
  periodosComparados,
  removerFiltros,
} from '@/lib/filtros-url'
import { opcoesFiltrosExemplo as opcoes } from '@/mocks/opcoes-filtros'

const url = (texto: string) => new URLSearchParams(texto)

describe('lerFiltros', () => {
  test('lê os valores válidos', () => {
    expect(
      lerFiltros(
        url(
          'base_de=2025-01&base_ate=2025-03&comparado_de=2026-01&municipio=Recife&bairro=Pina&classe=RURAL&alimentador=ALM-REC-001&causa=VEGETACAO',
        ),
        opcoes,
      ),
    ).toEqual({
      base_de: '2025-01',
      base_ate: '2025-03',
      comparado_de: '2026-01',
      municipio: 'Recife',
      bairro: 'Pina',
      classe: 'RURAL',
      alimentador: 'ALM-REC-001',
      causa: 'VEGETACAO',
    })
  })

  test('descarta valores que não existem', () => {
    expect(
      lerFiltros(
        url('base_de=2025-06&base_ate=2025-01&comparado_de=2030-01&municipio=Narnia&classe=XYZ&alimentador=ALM-X&causa=METEORO'),
        opcoes,
      ),
    ).toEqual({
      base_de: undefined,
      base_ate: undefined,
      comparado_de: undefined,
      municipio: undefined,
      bairro: undefined,
      classe: undefined,
      alimentador: undefined,
      causa: undefined,
    })
  })

  test('bairro de outro município ou sem município é descartado', () => {
    expect(lerFiltros(url('municipio=Olinda&bairro=Pina'), opcoes).bairro).toBeUndefined()
    expect(lerFiltros(url('bairro=Pina'), opcoes).bairro).toBeUndefined()
  })

  test('alimentador que não atende o município é descartado', () => {
    expect(lerFiltros(url('municipio=Olinda&alimentador=ALM-REC-001'), opcoes).alimentador).toBeUndefined()
    // Sem município, vale qualquer alimentador
    expect(lerFiltros(url('alimentador=ALM-REC-001'), opcoes).alimentador).toBe('ALM-REC-001')
  })

  test('o base precisa deixar espaço depois dele para um comparado de mesmo tamanho', () => {
    expect(lerFiltros(url('base_de=2023-01&base_ate=2023-03'), opcoes)).toMatchObject({
      base_de: '2023-01',
      base_ate: '2023-03',
    })
    expect(lerFiltros(url('base_de=2025-01&base_ate=2025-12'), opcoes)).toMatchObject({
      base_de: undefined,
      base_ate: undefined,
    })
    // Só um dos dois meses, ou mais de 24 meses
    expect(lerFiltros(url('base_de=2023-01'), opcoes).base_de).toBeUndefined()
    expect(lerFiltros(url('base_de=2022-07&base_ate=2024-07'), opcoes).base_de).toBeUndefined()
  })

  test('sem as opções carregadas, aceita os textos como vieram', () => {
    expect(lerFiltros(url('municipio=Qualquer&alimentador=ALM-X&causa=X'))).toMatchObject({
      municipio: 'Qualquer',
      alimentador: 'ALM-X',
      causa: 'X',
    })
  })
})

describe('aplicarFiltro e removerFiltros', () => {
  test('trocar o município zera o bairro', () => {
    expect(aplicarFiltro(url('municipio=Recife&bairro=Pina'), 'municipio', 'Olinda').toString()).toBe(
      'municipio=Olinda',
    )
  })

  test('trocar o município tira o alimentador só se ele não atender o novo município', () => {
    // ALM-JAB-002 atende Jaboatão e Recife
    expect(aplicarFiltro(url('alimentador=ALM-JAB-002'), 'municipio', 'Recife', opcoes).toString()).toBe(
      'alimentador=ALM-JAB-002&municipio=Recife',
    )
    expect(aplicarFiltro(url('alimentador=ALM-JAB-002'), 'municipio', 'Olinda', opcoes).toString()).toBe(
      'municipio=Olinda',
    )
    // Voltar para "Todos" mantém o alimentador
    expect(aplicarFiltro(url('municipio=Recife&alimentador=ALM-REC-001'), 'municipio', undefined, opcoes).toString()).toBe(
      'alimentador=ALM-REC-001',
    )
  })

  test('vários filtros de uma vez, como o começo e o fim do período', () => {
    expect(aplicarFiltros(url('classe=RURAL'), { base_de: '2025-01', base_ate: '2025-06' }).toString()).toBe(
      'classe=RURAL&base_de=2025-01&base_ate=2025-06',
    )
    expect(aplicarFiltros(url('base_de=2025-01&base_ate=2025-06'), { base_de: undefined, base_ate: undefined }).toString()).toBe('')
  })

  test('valor vazio remove o filtro', () => {
    expect(aplicarFiltro(url('classe=RURAL'), 'classe', undefined).toString()).toBe('')
  })

  test('limpar mantém os parâmetros que não são filtro', () => {
    expect(removerFiltros(url('aba=faturas&municipio=Recife&base_de=2023-01&base_ate=2023-03&comparado_de=2026-01&causa=VEGETACAO')).toString()).toBe('aba=faturas')
  })
})

describe('periodosComparados', () => {
  test('sem escolha, Indicadores e Continuidade mostram o último ano contra o anterior', () => {
    expect(periodosComparados(opcoes.competencias, {}, 'ano-anterior')).toEqual({
      base: { de: '2024-07', ate: '2025-06' },
      comparado: { de: '2025-07', ate: '2026-06' },
    })
  })

  test('sem escolha, a Receita compara o primeiro ano da base com o último', () => {
    expect(periodosComparados(opcoes.competencias, {}, 'inicio-da-base')).toEqual({
      base: { de: '2022-07', ate: '2023-06' },
      comparado: { de: '2025-07', ate: '2026-06' },
    })
  })

  test('com o base escolhido, o comparado tem o mesmo tamanho e, sem escolha, os mesmos meses', () => {
    const base = { base_de: '2023-01', base_ate: '2023-03' }
    expect(periodosComparados(opcoes.competencias, base, 'ano-anterior')).toEqual({
      base: { de: '2023-01', ate: '2023-03' },
      comparado: { de: '2026-01', ate: '2026-03' },
    })
    expect(periodosComparados(opcoes.competencias, { ...base, comparado_de: '2025-07' }, 'ano-anterior')).toEqual({
      base: { de: '2023-01', ate: '2023-03' },
      comparado: { de: '2025-07', ate: '2025-09' },
    })
  })

  test('comparado que não cabe com o base volta para o padrão', () => {
    // Começa antes do fim do base
    expect(
      periodosComparados(opcoes.competencias, { base_de: '2023-01', base_ate: '2023-03', comparado_de: '2023-02' }, 'ano-anterior')
        ?.comparado,
    ).toEqual({ de: '2026-01', ate: '2026-03' })
  })
})
