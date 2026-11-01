import { afterEach, describe, expect, test, vi } from 'vitest'
import { aplicarTema, CHAVE_TEMA, temaSalvo } from '@/lib/tema'

afterEach(() => {
  vi.restoreAllMocks()
  localStorage.clear()
  document.documentElement.classList.remove('dark')
})

describe('tema', () => {
  test('sem escolha salva, ou com um valor que não é tema, o portal fica no claro', () => {
    expect(temaSalvo()).toBe('claro')
    localStorage.setItem(CHAVE_TEMA, 'roxo')
    expect(temaSalvo()).toBe('claro')
  })

  test('o Dracula liga a classe dark e fica salvo; o claro tira a classe', () => {
    aplicarTema('dracula')
    expect(document.documentElement).toHaveClass('dark')
    expect(temaSalvo()).toBe('dracula')

    aplicarTema('claro')
    expect(document.documentElement).not.toHaveClass('dark')
    expect(temaSalvo()).toBe('claro')
  })

  test('com o armazenamento bloqueado, abre no claro e a troca vale na página aberta', () => {
    const bloqueado = () => {
      throw new Error('armazenamento bloqueado')
    }
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(bloqueado)
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(bloqueado)

    expect(temaSalvo()).toBe('claro')
    aplicarTema('dracula')
    expect(document.documentElement).toHaveClass('dark')
  })
})
