import { describe, expect, test } from 'vitest'
import { aplicarFiltro, lerFiltros, removerFiltros } from '@/lib/filtros-url'
import { opcoesFiltrosExemplo as opcoes } from '@/mocks/opcoes-filtros'

const url = (texto: string) => new URLSearchParams(texto)

describe('lerFiltros', () => {
  test('lê os valores válidos', () => {
    expect(
      lerFiltros(url('inicio=2025-07&fim=2026-06&municipio=Recife&bairro=Pina&classe=RURAL'), opcoes),
    ).toEqual({
      inicio: '2025-07',
      fim: '2026-06',
      municipio: 'Recife',
      bairro: 'Pina',
      classe: 'RURAL',
    })
  })

  test('descarta valores que não existem', () => {
    expect(lerFiltros(url('inicio=2025-13&fim=1999-01&municipio=Narnia&classe=XYZ'), opcoes)).toEqual({
      inicio: undefined,
      fim: undefined,
      municipio: undefined,
      bairro: undefined,
      classe: undefined,
    })
  })

  test('bairro de outro município ou sem município é descartado', () => {
    expect(lerFiltros(url('municipio=Olinda&bairro=Pina'), opcoes).bairro).toBeUndefined()
    expect(lerFiltros(url('bairro=Pina'), opcoes).bairro).toBeUndefined()
  })

  test('sem as opções carregadas, confere só o formato', () => {
    expect(lerFiltros(url('inicio=2030-01&municipio=Qualquer'))).toMatchObject({
      inicio: '2030-01',
      municipio: 'Qualquer',
    })
  })

  test('período invertido na URL é corrigido', () => {
    expect(lerFiltros(url('inicio=2026-01&fim=2025-07'), opcoes)).toMatchObject({
      inicio: '2025-07',
      fim: '2026-01',
    })
  })
})

describe('aplicarFiltro e removerFiltros', () => {
  test('trocar o município zera o bairro', () => {
    expect(aplicarFiltro(url('municipio=Recife&bairro=Pina'), 'municipio', 'Olinda').toString()).toBe(
      'municipio=Olinda',
    )
  })

  test('valor vazio remove o filtro', () => {
    expect(aplicarFiltro(url('classe=RURAL'), 'classe', undefined).toString()).toBe('')
  })

  test('o início nunca fica depois do fim', () => {
    expect(aplicarFiltro(url('fim=2025-01'), 'inicio', '2025-06').toString()).toBe('fim=2025-06&inicio=2025-06')
    expect(aplicarFiltro(url('inicio=2025-06'), 'fim', '2025-01').toString()).toBe('inicio=2025-01&fim=2025-01')
  })

  test('limpar mantém os parâmetros que não são filtro', () => {
    expect(removerFiltros(url('aba=faturas&municipio=Recife&classe=RURAL')).toString()).toBe('aba=faturas')
  })
})
