import { describe, expect, test } from 'vitest'
import { aplicarFiltro, janelaDoPeriodo, lerFiltros, removerFiltros } from '@/lib/filtros-url'
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
})
