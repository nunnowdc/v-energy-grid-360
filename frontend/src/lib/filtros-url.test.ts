import { describe, expect, test } from 'vitest'
import {
  aplicarFiltro,
  aplicarFiltros,
  lerFiltros,
  periodoEscolhido,
  periodosDaReceita,
  removerFiltros,
} from '@/lib/filtros-url'
import { opcoesFiltrosExemplo as opcoes } from '@/mocks/opcoes-filtros'

const url = (texto: string) => new URLSearchParams(texto)

describe('lerFiltros', () => {
  test('lê os valores válidos', () => {
    expect(
      lerFiltros(
        url('de=2025-01&ate=2025-06&municipio=Recife&bairro=Pina&classe=RURAL&alimentador=ALM-REC-001&causa=VEGETACAO'),
        opcoes,
      ),
    ).toEqual({
      de: '2025-01',
      ate: '2025-06',
      municipio: 'Recife',
      bairro: 'Pina',
      classe: 'RURAL',
      alimentador: 'ALM-REC-001',
      causa: 'VEGETACAO',
    })
  })

  test('descarta valores que não existem', () => {
    expect(
      lerFiltros(url('de=2025-06&ate=2025-01&municipio=Narnia&classe=XYZ&alimentador=ALM-X&causa=METEORO'), opcoes),
    ).toEqual({
      de: undefined,
      ate: undefined,
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

  test('o período só vale com o anterior, de mesmo tamanho, dentro da base', () => {
    expect(lerFiltros(url('de=2022-10&ate=2022-12'), opcoes)).toMatchObject({ de: '2022-10', ate: '2022-12' })
    // jul a set/2022 não tem os 3 meses anteriores na base
    expect(lerFiltros(url('de=2022-07&ate=2022-09'), opcoes)).toMatchObject({ de: undefined, ate: undefined })
    // Só um dos dois meses, ou mais de 24 meses
    expect(lerFiltros(url('de=2025-01'), opcoes)).toMatchObject({ de: undefined, ate: undefined })
    expect(lerFiltros(url('de=2024-06&ate=2026-06'), opcoes)).toMatchObject({ de: undefined, ate: undefined })
  })

  test('na Receita, base inválido volta tudo ao padrão e comparado inválido volta só ele', () => {
    expect(lerFiltros(url('base_de=2023-01&base_ate=2023-03&comparado_de=2025-07'), opcoes)).toMatchObject({
      base_de: '2023-01',
      base_ate: '2023-03',
      comparado_de: '2025-07',
    })
    // Comparado antes do fim do base
    expect(lerFiltros(url('base_de=2023-01&base_ate=2023-03&comparado_de=2023-02'), opcoes)).toMatchObject({
      base_de: '2023-01',
      comparado_de: undefined,
    })
    // Base sem espaço depois dele para um comparado de mesmo tamanho
    expect(lerFiltros(url('base_de=2025-01&base_ate=2025-12&comparado_de=2026-01'), opcoes)).toMatchObject({
      base_de: undefined,
      base_ate: undefined,
      comparado_de: undefined,
    })
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
    expect(aplicarFiltros(url('classe=RURAL'), { de: '2025-01', ate: '2025-06' }).toString()).toBe(
      'classe=RURAL&de=2025-01&ate=2025-06',
    )
    expect(aplicarFiltros(url('de=2025-01&ate=2025-06'), { de: undefined, ate: undefined }).toString()).toBe('')
  })

  test('valor vazio remove o filtro', () => {
    expect(aplicarFiltro(url('classe=RURAL'), 'classe', undefined).toString()).toBe('')
  })

  test('limpar mantém os parâmetros que não são filtro', () => {
    expect(removerFiltros(url('aba=faturas&municipio=Recife&de=2026-04&ate=2026-06&base_de=2023-01&causa=VEGETACAO')).toString()).toBe('aba=faturas')
  })
})

describe('períodos em vigor', () => {
  test('sem escolha, os últimos 12 meses da base, não da data de hoje', () => {
    expect(periodoEscolhido(opcoes.competencias, {})).toEqual({ de: '2025-07', ate: '2026-06' })
    expect(periodoEscolhido(opcoes.competencias, { de: '2025-01', ate: '2025-03' })).toEqual({
      de: '2025-01',
      ate: '2025-03',
    })
  })

  test('Receita sem escolha: primeiro ano da base contra os mesmos meses do último ano', () => {
    expect(periodosDaReceita(opcoes.competencias, {})).toEqual({
      base: { de: '2022-07', ate: '2023-06' },
      comparado: { de: '2025-07', ate: '2026-06' },
    })
  })

  test('com só o base escolhido, o comparado tem o mesmo tamanho e os mesmos meses', () => {
    expect(periodosDaReceita(opcoes.competencias, { base_de: '2023-01', base_ate: '2023-03' })).toEqual({
      base: { de: '2023-01', ate: '2023-03' },
      comparado: { de: '2026-01', ate: '2026-03' },
    })
    expect(
      periodosDaReceita(opcoes.competencias, { base_de: '2023-01', base_ate: '2023-03', comparado_de: '2025-07' }),
    ).toEqual({
      base: { de: '2023-01', ate: '2023-03' },
      comparado: { de: '2025-07', ate: '2025-09' },
    })
  })
})
