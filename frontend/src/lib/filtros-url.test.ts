import { describe, expect, test } from 'vitest'
import { anosDaBase, aplicarFiltro, janelaDoPeriodo, lerFiltros, mesesFinais, removerFiltros } from '@/lib/filtros-url'
import { opcoesFiltrosExemplo as opcoes } from '@/mocks/opcoes-filtros'

const url = (texto: string) => new URLSearchParams(texto)

describe('lerFiltros', () => {
  test('lê os valores válidos', () => {
    expect(
      lerFiltros(
        url('meses=6&municipio=Recife&bairro=Pina&classe=RURAL&alimentador=ALM-REC-001&causa=VEGETACAO'),
        opcoes,
      ),
    ).toEqual({
      meses: 6,
      municipio: 'Recife',
      bairro: 'Pina',
      classe: 'RURAL',
      alimentador: 'ALM-REC-001',
      causa: 'VEGETACAO',
    })
  })

  test('descarta valores que não existem', () => {
    expect(
      lerFiltros(url('meses=5&municipio=Narnia&classe=XYZ&alimentador=ALM-X&causa=METEORO'), opcoes),
    ).toEqual({
      meses: undefined,
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

  test('"Até" vale se antes dele couber o período anterior, de mesmo tamanho', () => {
    expect(lerFiltros(url('meses=3&ate=2022-12'), opcoes).ate).toBe('2022-12')
    expect(lerFiltros(url('meses=3&ate=2022-11'), opcoes).ate).toBeUndefined()
    expect(lerFiltros(url('ate=2024-06'), opcoes).ate).toBe('2024-06')
    expect(lerFiltros(url('ate=2024-05'), opcoes).ate).toBeUndefined()
    expect(lerFiltros(url('ate=2030-01'), opcoes).ate).toBeUndefined()
  })

  test('os anos da Receita são começos de ano da base, com o comparado depois do base', () => {
    expect(lerFiltros(url('base=2023-07&comparado=2024-07'), opcoes)).toMatchObject({
      base: '2023-07',
      comparado: '2024-07',
    })
    // Só um escolhido: o outro fica no padrão
    expect(lerFiltros(url('base=2024-07'), opcoes)).toMatchObject({ base: '2024-07', comparado: undefined })
    // Mês que não começa um ano da base
    expect(lerFiltros(url('base=2023-01'), opcoes).base).toBeUndefined()
    // Comparado antes do base, ou igual a ele: volta tudo para o padrão
    expect(lerFiltros(url('base=2024-07&comparado=2023-07'), opcoes)).toMatchObject({
      base: undefined,
      comparado: undefined,
    })
    expect(lerFiltros(url('base=2025-07'), opcoes)).toMatchObject({ base: undefined, comparado: undefined })
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

  test('trocar o tamanho do período tira o "Até" que deixou de caber', () => {
    expect(aplicarFiltro(url('ate=2024-06'), 'meses', '3', opcoes).toString()).toBe('ate=2024-06&meses=3')
    expect(aplicarFiltro(url('meses=3&ate=2023-06'), 'meses', undefined, opcoes).toString()).toBe('')
  })

  test('valor vazio remove o filtro', () => {
    expect(aplicarFiltro(url('classe=RURAL'), 'classe', undefined).toString()).toBe('')
  })

  test('limpar mantém os parâmetros que não são filtro', () => {
    expect(removerFiltros(url('aba=faturas&municipio=Recife&meses=3&causa=VEGETACAO')).toString()).toBe('aba=faturas')
  })
})

describe('janelaDoPeriodo', () => {
  test('termina no último mês da base, não na data de hoje', () => {
    expect(janelaDoPeriodo(opcoes.competencias)).toEqual({ inicio: '2025-07', fim: '2026-06' })
    expect(janelaDoPeriodo(opcoes.competencias, 3)).toEqual({ inicio: '2026-04', fim: '2026-06' })
  })

  test('com "Até", termina no mês escolhido', () => {
    expect(janelaDoPeriodo(opcoes.competencias, 6, '2024-12')).toEqual({ inicio: '2024-07', fim: '2024-12' })
  })

  test('o fim mais antigo deixa espaço para o período anterior', () => {
    expect(mesesFinais(opcoes.competencias, 12)[0]).toBe('2024-06')
    expect(mesesFinais(opcoes.competencias, 3)[0]).toBe('2022-12')
  })
})

describe('anosDaBase', () => {
  test('anos de 12 meses contados do fim da base', () => {
    expect(anosDaBase(opcoes.competencias)).toEqual([
      { inicio: '2022-07', fim: '2023-06' },
      { inicio: '2023-07', fim: '2024-06' },
      { inicio: '2024-07', fim: '2025-06' },
      { inicio: '2025-07', fim: '2026-06' },
    ])
    // Base que não fecha em anos inteiros: o pedaço que sobra no começo fica de fora
    expect(anosDaBase(opcoes.competencias.slice(3)).map(({ inicio }) => inicio)).toEqual([
      '2023-07',
      '2024-07',
      '2025-07',
    ])
  })
})
