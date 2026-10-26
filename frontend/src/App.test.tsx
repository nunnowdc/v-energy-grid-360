import { render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import App from '@/App'
import type { Perfil } from '@/config/perfis'

// Perfil do usuário em cada teste
const perfil = vi.hoisted(() => ({ atual: 'ADMIN_TI' as Perfil }))

vi.mock('@/hooks/use-usuario', async () => {
  const { permissoesPorPerfil } = await import('@/config/perfis')
  return {
    useUsuario: () => {
      const permissoes = permissoesPorPerfil[perfil.atual]
      return {
        usuario: { nome: 'Teste', perfil: perfil.atual, permissoes },
        pode: (permissao: string) => (permissoes as string[]).includes(permissao),
      }
    },
  }
})

// A barra de filtros e o selo da base buscam dados no backend; aqui só importam as rotas
vi.mock('@/components/FiltrosGlobais/FiltrosGlobais', () => ({ default: () => null }))
vi.mock('@/hooks/use-opcoes-filtros', () => ({ useOpcoesFiltros: () => ({ data: undefined }) }))

function abrir(url: string, comPerfil: Perfil) {
  perfil.atual = comPerfil
  window.history.pushState({}, '', url)
  render(<App />)
}

const titulo = () => screen.getByRole('heading', { level: 1 }).textContent
const trilha = () => screen.getByRole('navigation', { name: 'Você está em' }).textContent
const menu = () => document.querySelector('[data-sidebar="content"]') as HTMLElement
const telasNoMenu = () =>
  within(menu())
    .getAllByRole('link')
    .map((link) => link.textContent)

beforeEach(() => {
  window.history.pushState({}, '', '/')
})

describe('menu e rotas por perfil', () => {
  test('Diretoria vê só as telas dela no menu', () => {
    abrir('/', 'DIRETORIA')
    expect(titulo()).toBe('Indicadores')
    expect(telasNoMenu()).toEqual(['Indicadores', 'Receita', 'Continuidade'])
  })

  test('o menu agrupa as telas e esconde grupo sem tela permitida', () => {
    abrir('/', 'ADMIN_TI')
    expect(within(menu()).getByText('Negócio')).toBeInTheDocument()
    expect(within(menu()).getByText('Operação')).toBeInTheDocument()
    document.body.innerHTML = ''

    abrir('/', 'ATENDIMENTO')
    expect(within(menu()).queryByText('Negócio')).not.toBeInTheDocument()
    expect(within(menu()).getByText('Operação')).toBeInTheDocument()
  })

  test('Atendimento abre o "/" e vai direto para a Visão 360', () => {
    abrir('/', 'ATENDIMENTO')
    expect(window.location.pathname).toBe('/visao-360')
    expect(titulo()).toBe('Visão 360')
  })

  test('a trilha mostra o grupo e a tela', () => {
    abrir('/receita', 'DIRETORIA')
    expect(trilha()).toBe('Negócio/Receita')
  })

  test('endereço de tela sem permissão mostra "Sem permissão"', () => {
    abrir('/receita', 'ATENDIMENTO')
    expect(titulo()).toBe('Você não tem acesso a esta tela')
    expect(trilha()).toBe('Sem permissão')
  })

  test('endereço que não existe mostra "Página não encontrada"', () => {
    abrir('/nao-existe', 'ADMIN_TI')
    expect(titulo()).toBe('Página não encontrada')
  })

  test('o login abre fora do layout, sem o menu', () => {
    abrir('/login?motivo=sessao-expirada', 'ADMIN_TI')
    expect(screen.getByText('Entrar no portal')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('Sua sessão expirou')
    expect(menu()).toBeNull()
  })
})
