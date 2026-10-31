import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import App from '@/App'
import type { Perfil } from '@/config/perfis'
import { queryClient } from '@/lib/api/query-client'
import { navegador } from '@/lib/api/sessao'
import { usuarioApiExemplo } from '@/mocks/usuarios'

// A barra de filtros e o selo da base buscam dados no backend; aqui só importam as rotas
vi.mock('@/components/FiltrosGlobais/FiltrosGlobais', () => ({ default: () => null }))
vi.mock('@/hooks/use-opcoes-filtros', () => ({ useOpcoesFiltros: () => ({ data: undefined }) }))

const json = (corpo: unknown, status = 200) =>
  new Response(JSON.stringify(corpo), { status, headers: { 'Content-Type': 'application/json' } })

// Backend falso: o /auth/me responde com o perfil do teste (null = ninguém logado)
// e o logout funciona; as rotas de dados não importam aqui
function backend(perfil: Perfil | null) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
    const caminho = String(url)
    if (caminho === '/api/auth/me') {
      return perfil ? json(usuarioApiExemplo(perfil)) : json({ detail: 'Não autenticado' }, 401)
    }
    if (caminho === '/api/auth/logout') {
      return new Response(null, { status: 204 })
    }
    return json({ detail: 'Não encontrado' }, 404)
  })
}

// O portal usa um cache só (o de lib/api/query-client), então cada teste começa do zero
async function abrir(url: string, perfil: Perfil | null) {
  backend(perfil)
  window.history.pushState({}, '', url)
  render(<App />)
  if (perfil) {
    await screen.findByRole('heading', { level: 1 })
  }
}

const titulo = () => screen.getByRole('heading', { level: 1 }).textContent
const trilha = () => screen.getByRole('navigation', { name: 'Você está em' }).textContent
const menu = () => document.querySelector('[data-sidebar="content"]') as HTMLElement
const telasNoMenu = () =>
  within(menu())
    .getAllByRole('link')
    .map((link) => link.textContent)

beforeEach(() => {
  queryClient.clear()
  window.history.pushState({}, '', '/')
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('menu e rotas por perfil', () => {
  test('Diretoria vê só as telas dela no menu', async () => {
    await abrir('/', 'DIRETORIA')
    expect(titulo()).toBe('Indicadores')
    expect(telasNoMenu()).toEqual(['Indicadores', 'Receita', 'Continuidade'])
  })

  test('o menu agrupa as telas e esconde grupo sem tela permitida', async () => {
    await abrir('/', 'ADMIN_TI')
    expect(within(menu()).getByText('Negócio')).toBeInTheDocument()
    expect(within(menu()).getByText('Operação')).toBeInTheDocument()
    document.body.innerHTML = ''
    queryClient.clear()

    await abrir('/', 'ATENDIMENTO')
    expect(within(menu()).queryByText('Negócio')).not.toBeInTheDocument()
    expect(within(menu()).getByText('Operação')).toBeInTheDocument()
  })

  test('Atendimento abre o "/" e vai direto para a Visão 360', async () => {
    await abrir('/', 'ATENDIMENTO')
    expect(window.location.pathname).toBe('/visao-360')
    expect(titulo()).toBe('Visão 360')
  })

  test('a trilha mostra o grupo e a tela', async () => {
    await abrir('/receita', 'DIRETORIA')
    expect(trilha()).toBe('Negócio/Receita')
  })

  test('endereço de tela sem permissão mostra "Sem permissão"', async () => {
    await abrir('/receita', 'ATENDIMENTO')
    expect(titulo()).toBe('Você não tem acesso a esta tela')
    expect(trilha()).toBe('Sem permissão')
  })

  test('endereço que não existe mostra "Página não encontrada"', async () => {
    await abrir('/nao-existe', 'ADMIN_TI')
    expect(titulo()).toBe('Página não encontrada')
  })

  test('o agente de IA abre ao lado da tela, que continua aberta, em qualquer perfil', async () => {
    await abrir('/receita', 'DIRETORIA')
    const botao = screen.getByRole('button', { name: 'Agente de IA' })
    expect(botao).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('complementary', { name: 'Agente de IA' })).not.toBeInTheDocument()

    fireEvent.click(botao)
    expect(botao).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('complementary', { name: 'Agente de IA' })).toBeInTheDocument()
    expect(titulo()).toBe('Receita')

    fireEvent.click(screen.getByRole('button', { name: 'Fechar o agente' }))
    expect(screen.queryByRole('complementary', { name: 'Agente de IA' })).not.toBeInTheDocument()
    document.body.innerHTML = ''
    queryClient.clear()

    await abrir('/visao-360', 'ATENDIMENTO')
    expect(screen.getByRole('button', { name: 'Agente de IA' })).toBeInTheDocument()
  })

  test('o rodapé do menu mostra quem está logado', async () => {
    await abrir('/', 'OPERACAO')
    expect(screen.getByText('Pessoa Operação')).toBeInTheDocument()
    expect(within(screen.getByText('Pessoa Operação').parentElement!).getByText('Operação')).toBeInTheDocument()
  })
})

describe('login e sessão', () => {
  test('sem login, qualquer tela leva ao login e guarda o endereço para voltar', async () => {
    await abrir('/continuidade?alimentador=ALM-REC-001', null)
    expect(await screen.findByText('Entrar no portal')).toBeInTheDocument()
    expect(window.location.pathname + window.location.search).toBe(
      '/login?voltar=%2Fcontinuidade%3Falimentador%3DALM-REC-001',
    )
    // Visita sem sessão não é "sessão expirada"
    expect(screen.queryByText(/Sua sessão expirou/)).not.toBeInTheDocument()
    expect(menu()).toBeNull()
  })

  test('enquanto o /auth/me não responde, nada de menu nem de dados', () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise<Response>(() => {}))
    window.history.pushState({}, '', '/receita')
    render(<App />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando o portal')
    expect(menu()).toBeNull()
    expect(screen.queryByRole('heading', { level: 1 })).not.toBeInTheDocument()
  })

  test('se o /auth/me falhar, mostra o erro com "Tentar de novo"', async () => {
    let falhar = true
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () =>
      falhar ? json({ detail: 'Erro interno' }, 500) : json(usuarioApiExemplo('DIRETORIA')),
    )
    window.history.pushState({}, '', '/receita')
    render(<App />)

    // A falha de servidor tenta mais 1 vez sozinha antes de mostrar o erro
    expect(await screen.findByRole('alert', {}, { timeout: 5000 })).toHaveTextContent('Erro interno')
    expect(menu()).toBeNull()
    falhar = false
    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }))
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent('Receita')
  })

  test('a tela de login abre fora do layout, sem o menu, e avisa da sessão expirada', async () => {
    await abrir('/login?motivo=sessao-expirada', null)
    expect(await screen.findByText('Entrar no portal')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Sua sessão expirou')
    expect(menu()).toBeNull()
  })

  test('"Sair" chama o logout e recarrega o portal no login', async () => {
    const abrirPagina = vi.spyOn(navegador, 'abrir').mockImplementation(() => {})
    await abrir('/', 'DIRETORIA')
    const fetch = vi.mocked(globalThis.fetch)

    fireEvent.click(screen.getByRole('button', { name: 'Sair' }))

    await waitFor(() => expect(abrirPagina).toHaveBeenCalledWith('/login'))
    expect(fetch.mock.calls.some(([url, init]) => url === '/api/auth/logout' && init?.method === 'POST')).toBe(true)
  })
})
