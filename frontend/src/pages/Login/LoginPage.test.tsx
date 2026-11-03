import { fireEvent, screen } from '@testing-library/react'
import { Route, Routes, useLocation } from 'react-router'
import { afterEach, expect, test, vi } from 'vitest'
import type { Perfil } from '@/config/perfis'
import { CHAVE_SESSAO } from '@/hooks/use-usuario'
import { usuarioApiExemplo } from '@/mocks/usuarios'
import LoginPage from '@/pages/Login/LoginPage'
import { renderizar } from '@/test/renderizar'

// Backend falso do POST /api/auth/login
function backend(status: number, corpo: unknown) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(
    async () => new Response(JSON.stringify(corpo), { status, headers: { 'Content-Type': 'application/json' } }),
  )
}

// Mostra para onde o login levou
function Endereco() {
  const { pathname, search } = useLocation()
  return <output aria-label="Endereço">{pathname + search}</output>
}

function abrir(url = '/login', perfil: Perfil | null = null) {
  return renderizar(
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="*" element={<Endereco />} />
    </Routes>,
    { url, perfil },
  )
}

function entrarCom(email: string, senha: string) {
  fireEvent.change(screen.getByLabelText('E-mail'), { target: { value: email } })
  fireEvent.change(screen.getByLabelText('Senha'), { target: { value: senha } })
  fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
}

afterEach(() => {
  vi.restoreAllMocks()
})

test('entra com e-mail e senha e vai para o portal', async () => {
  const fetch = backend(200, usuarioApiExemplo('DIRETORIA'))
  const { queryClient } = abrir()

  entrarCom('  diretoria@example.test ', 'senha-de-teste')

  expect(await screen.findByLabelText('Endereço')).toHaveTextContent(/^\/$/)
  const [url, init] = fetch.mock.calls[0]
  expect(url).toBe('/api/auth/login')
  expect(init?.method).toBe('POST')
  expect(JSON.parse(String(init?.body))).toEqual({ email: 'diretoria@example.test', senha: 'senha-de-teste' })
  expect(queryClient.getQueryData(CHAVE_SESSAO)).toMatchObject({ perfil: 'DIRETORIA' })
})

test('volta para a tela pedida antes do login, se o perfil puder abri-la', async () => {
  backend(200, usuarioApiExemplo('OPERACAO'))
  abrir('/login?voltar=%2Fcontinuidade%3Falimentador%3DALM-REC-001')

  entrarCom('operacao@example.test', 'senha-de-teste')

  expect(await screen.findByLabelText('Endereço')).toHaveTextContent('/continuidade?alimentador=ALM-REC-001')
})

test('tela pedida que o perfil não abre vira a primeira tela dele', async () => {
  backend(200, usuarioApiExemplo('ATENDIMENTO'))
  abrir('/login?voltar=%2Freceita')

  entrarCom('atendimento@example.test', 'senha-de-teste')

  expect(await screen.findByLabelText('Endereço')).toHaveTextContent(/^\/$/)
})

test('o login apaga do cache os dados da conta anterior', async () => {
  backend(200, usuarioApiExemplo('PERDAS'))
  const { queryClient } = abrir()
  queryClient.setQueryData(['receita', 'de outra conta'], { total: 1 })

  entrarCom('perdas@example.test', 'senha-de-teste')

  await screen.findByLabelText('Endereço')
  expect(queryClient.getQueryData(['receita', 'de outra conta'])).toBeUndefined()
})

test('credenciais erradas mostram a mensagem genérica e continuam no login', async () => {
  backend(401, { detail: 'Credenciais inválidas' })
  abrir()

  entrarCom('diretoria@example.test', 'errada')

  expect(await screen.findByRole('alert')).toHaveTextContent('E-mail ou senha incorretos.')
  expect(screen.getByLabelText('Senha')).toHaveAttribute('aria-invalid', 'true')
  expect(screen.queryByLabelText('Endereço')).not.toBeInTheDocument()
})

test('backend fora do ar mostra o erro sem sair do login', async () => {
  backend(503, { detail: 'Banco de dados indisponível no momento.' })
  abrir()

  entrarCom('diretoria@example.test', 'senha-de-teste')

  expect(await screen.findByRole('alert')).toHaveTextContent('Banco de dados indisponível no momento.')
})

test('campos vazios ou e-mail sem @ nem chegam ao backend', () => {
  const fetch = backend(200, usuarioApiExemplo())
  abrir()

  fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
  expect(screen.getByRole('alert')).toHaveTextContent('Preencha o e-mail e a senha.')

  entrarCom('diretoria', 'senha-de-teste')
  expect(screen.getByRole('alert')).toHaveTextContent('Digite um e-mail válido.')
  expect(fetch).not.toHaveBeenCalled()
})

test('depois de a sessão expirar, avisa antes do formulário', () => {
  abrir('/login?motivo=sessao-expirada')
  expect(screen.getByRole('status')).toHaveTextContent('Sua sessão expirou. Entre novamente.')
  expect(screen.getByRole('button', { name: 'Entrar' })).toBeInTheDocument()
})

test('quem já está logado sai do login direto para o portal', () => {
  abrir('/login', 'ADMIN_TI')
  expect(screen.getByLabelText('Endereço')).toHaveTextContent(/^\/$/)
})
