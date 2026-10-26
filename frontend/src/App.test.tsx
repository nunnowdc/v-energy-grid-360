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

// A barra de filtros busca dados no backend; aqui só importam as rotas
vi.mock('@/components/FiltrosGlobais/FiltrosGlobais', () => ({ default: () => null }))

function abrir(url: string, comPerfil: Perfil) {
  perfil.atual = comPerfil
  window.history.pushState({}, '', url)
  render(<App />)
}

const titulo = () => screen.getByRole('heading', { level: 1 }).textContent
const telasNoMenu = () =>
  within(screen.getByText('Telas').parentElement!)
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

  test('Atendimento abre o "/" e vai direto para a Visão 360', () => {
    abrir('/', 'ATENDIMENTO')
    expect(window.location.pathname).toBe('/visao-360')
    expect(titulo()).toBe('Visão 360')
  })

  test('endereço de tela sem permissão mostra "Sem permissão"', () => {
    abrir('/receita', 'ATENDIMENTO')
    expect(titulo()).toBe('Sem permissão')
    expect(screen.getByText('Você não tem acesso a esta tela')).toBeInTheDocument()
  })

  test('endereço que não existe mostra "Página não encontrada"', () => {
    abrir('/nao-existe', 'ADMIN_TI')
    expect(titulo()).toBe('Página não encontrada')
  })

  test('o login abre fora do layout, sem o menu', () => {
    abrir('/login?motivo=sessao-expirada', 'ADMIN_TI')
    expect(screen.getByText('Entrar no portal')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('Sua sessão expirou')
    expect(screen.queryByText('Telas')).not.toBeInTheDocument()
  })
})
