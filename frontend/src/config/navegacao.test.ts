import { describe, expect, test } from 'vitest'
import { buscarItemAtual, estaAtivo, itensPermitidos } from '@/config/navegacao'
import { permissoesPorPerfil } from '@/config/perfis'

const telasDoPerfil = (perfil: keyof typeof permissoesPorPerfil) =>
  itensPermitidos(permissoesPorPerfil[perfil]).map((item) => item.label)

describe('estaAtivo', () => {
  test('a raiz só fica ativa no endereço exato', () => {
    expect(estaAtivo('/', '/')).toBe(true)
    expect(estaAtivo('/receita', '/')).toBe(false)
  })

  test('as outras telas também valem para sub-rotas', () => {
    expect(estaAtivo('/visao-360/UC129001', '/visao-360')).toBe(true)
    expect(estaAtivo('/visao-3600', '/visao-360')).toBe(false)
  })
})

test('buscarItemAtual encontra a tela pelo endereço', () => {
  expect(buscarItemAtual('/visao-360/UC129001')?.label).toBe('Visão 360')
  expect(buscarItemAtual('/nao-existe')).toBeUndefined()
})

test('cada perfil vê as telas da matriz combinada pelo time, e todos usam o agente', () => {
  expect(telasDoPerfil('DIRETORIA')).toEqual(['Indicadores', 'Receita', 'Continuidade', 'Agente de IA'])
  expect(telasDoPerfil('ATENDIMENTO')).toEqual(['Visão 360', 'Agente de IA'])
  expect(telasDoPerfil('PERDAS')).toEqual(['Visão 360', 'Fila de inspeção', 'Agente de IA'])
  expect(telasDoPerfil('OPERACAO')).toEqual(['Continuidade', 'Agente de IA'])
  expect(telasDoPerfil('ADMIN_TI')).toHaveLength(6)
})
