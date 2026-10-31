import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import TrocaSenha from '@/components/TrocaSenha/TrocaSenha'
import { renderizar } from '@/test/renderizar'

// Backend falso do PATCH /api/auth/password
function backend(status: number, corpo?: unknown) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(
    async () =>
      new Response(corpo === undefined ? null : JSON.stringify(corpo), {
        status,
        headers: { 'Content-Type': 'application/json' },
      }),
  )
}

function abrirPainel() {
  renderizar(<TrocaSenha />, { perfil: 'DIRETORIA' })
  fireEvent.click(screen.getByRole('button', { name: 'Trocar senha' }))
  return screen.getByRole('dialog', { name: 'Trocar senha' })
}

function trocar(painel: HTMLElement, atual: string, nova: string, confirmacao = nova) {
  fireEvent.change(within(painel).getByLabelText('Senha atual'), { target: { value: atual } })
  fireEvent.change(within(painel).getByLabelText('Nova senha'), { target: { value: nova } })
  fireEvent.change(within(painel).getByLabelText('Repita a nova senha'), { target: { value: confirmacao } })
  fireEvent.click(within(painel).getByRole('button', { name: 'Trocar senha' }))
}

afterEach(() => {
  vi.restoreAllMocks()
})

test('troca a senha e avisa que a sessão continua', async () => {
  const fetch = backend(204)
  const painel = abrirPainel()

  trocar(painel, 'senha-atual-1', 'senha-nova-2')

  expect(await within(painel).findByRole('status')).toHaveTextContent('Senha trocada.')
  const [url, init] = fetch.mock.calls[0]
  expect(url).toBe('/api/auth/password')
  expect(init?.method).toBe('PATCH')
  expect(JSON.parse(String(init?.body))).toEqual({ senha_atual: 'senha-atual-1', nova_senha: 'senha-nova-2' })

  fireEvent.click(within(painel).getByRole('button', { name: 'Fechar' }))
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
})

test('senha atual errada aparece no campo da senha atual', async () => {
  backend(400, { detail: 'Senha atual inválida' })
  const painel = abrirPainel()

  trocar(painel, 'errada-123', 'senha-nova-2')

  expect(await within(painel).findByText('A senha atual está incorreta.')).toBeInTheDocument()
  expect(within(painel).getByLabelText('Senha atual')).toHaveAttribute('aria-invalid', 'true')
  expect(within(painel).queryByRole('alert')).not.toBeInTheDocument()
})

test('nova senha curta, igual à atual ou com a confirmação diferente nem chega ao backend', () => {
  const fetch = backend(204)
  const painel = abrirPainel()

  trocar(painel, '', 'curta')
  expect(within(painel).getByText('Preencha a senha atual.')).toBeInTheDocument()
  expect(within(painel).getByText('A nova senha precisa de pelo menos 8 caracteres.')).toBeInTheDocument()

  trocar(painel, 'senha-atual-1', 'senha-atual-1')
  expect(within(painel).getByText('A nova senha precisa ser diferente da atual.')).toBeInTheDocument()

  trocar(painel, 'senha-atual-1', 'senha-nova-2', 'senha-nova-3')
  expect(within(painel).getByText('As duas senhas novas estão diferentes.')).toBeInTheDocument()
  expect(fetch).not.toHaveBeenCalled()
})

test('fechar e abrir o painel de novo começa com os campos vazios', async () => {
  backend(204)
  const painel = abrirPainel()
  fireEvent.change(within(painel).getByLabelText('Senha atual'), { target: { value: 'digitada' } })

  fireEvent.keyDown(painel, { key: 'Escape' })
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: 'Trocar senha' }))

  expect(within(screen.getByRole('dialog')).getByLabelText('Senha atual')).toHaveValue('')
})
