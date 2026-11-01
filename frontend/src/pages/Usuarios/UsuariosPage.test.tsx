import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { usuarioApiExemplo } from '@/mocks/usuarios'
import UsuariosPage from '@/pages/Usuarios/UsuariosPage'
import { renderizar } from '@/test/renderizar'

// Backend falso do POST /api/auth/users
function backend(status: number, corpo: unknown) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(
    async () => new Response(JSON.stringify(corpo), { status, headers: { 'Content-Type': 'application/json' } }),
  )
}

const abrir = () => renderizar(<UsuariosPage />, { url: '/usuarios' })
const formulario = () => screen.getByRole('button', { name: 'Criar conta' }).closest('form')!
const digitar = (rotulo: string, valor: string) =>
  fireEvent.change(within(formulario()).getByLabelText(rotulo), { target: { value: valor } })
// Como um clique de verdade: aperta e solta o botão do mouse em cima da opção
function escolherPerfil(nome: string) {
  fireEvent.click(screen.getByRole('combobox', { name: 'Perfil' }))
  const opcao = screen.getByRole('option', { name: nome })
  fireEvent.pointerDown(opcao, { pointerType: 'mouse' })
  fireEvent.click(opcao)
}
const criar = () => fireEvent.click(screen.getByRole('button', { name: 'Criar conta' }))

afterEach(() => {
  vi.restoreAllMocks()
})

test('cria a conta com o perfil escolhido e explica como passar a senha', async () => {
  const fetch = backend(201, { ...usuarioApiExemplo('PERDAS'), nome: 'Rafael Lima', email: 'rafael@example.test' })
  abrir()

  digitar('Nome', '  Rafael Lima ')
  digitar('E-mail', ' Rafael@Example.test ')
  escolherPerfil('Perdas')
  digitar('Senha inicial', 'senha-inicial-1')
  criar()

  expect(await screen.findByRole('status')).toHaveTextContent(
    'Conta criada para Rafael Lima (rafael@example.test), com o perfil Perdas.',
  )
  const [url, init] = fetch.mock.calls[0]
  expect(url).toBe('/api/auth/users')
  expect(init?.method).toBe('POST')
  expect(JSON.parse(String(init?.body))).toEqual({
    nome: 'Rafael Lima',
    email: 'Rafael@Example.test',
    perfil: 'PERDAS',
    senha: 'senha-inicial-1',
  })
  // Pronto para a próxima conta
  expect(within(formulario()).getByLabelText('Nome')).toHaveValue('')
  expect(within(formulario()).getByLabelText('Senha inicial')).toHaveValue('')
})

test('campos vazios ou inválidos mostram o erro em cada campo e nem chegam ao backend', () => {
  const fetch = backend(201, usuarioApiExemplo())
  abrir()

  criar()
  expect(screen.getByText('Preencha o nome.')).toBeInTheDocument()
  expect(screen.getByText('Preencha o e-mail.')).toBeInTheDocument()
  expect(screen.getByText('Escolha o perfil.')).toBeInTheDocument()
  expect(screen.getByText('A senha precisa de pelo menos 8 caracteres.')).toBeInTheDocument()
  expect(within(formulario()).getByLabelText('Nome')).toHaveAttribute('aria-invalid', 'true')

  digitar('E-mail', 'rafael')
  digitar('Senha inicial', 'curta')
  criar()
  expect(screen.getByText('Digite um e-mail válido.')).toBeInTheDocument()
  expect(fetch).not.toHaveBeenCalled()
})

test('e-mail que já tem conta mostra o erro no campo do e-mail', async () => {
  backend(409, { detail: 'Email já cadastrado' })
  abrir()

  digitar('Nome', 'Rafael Lima')
  digitar('E-mail', 'rafael@example.test')
  escolherPerfil('Perdas')
  digitar('Senha inicial', 'senha-inicial-1')
  criar()

  expect(await screen.findByText('Já existe uma conta com este e-mail.')).toBeInTheDocument()
  expect(within(formulario()).getByLabelText('E-mail')).toHaveAttribute('aria-invalid', 'true')
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})

test('outro erro do backend aparece embaixo do formulário', async () => {
  backend(503, { detail: 'Autenticação indisponível' })
  abrir()

  digitar('Nome', 'Rafael Lima')
  digitar('E-mail', 'rafael@example.test')
  escolherPerfil('Perdas')
  digitar('Senha inicial', 'senha-inicial-1')
  criar()

  expect(await screen.findByRole('alert')).toHaveTextContent('Autenticação indisponível')
})

test('mostra as telas de cada perfil, ao lado e embaixo do perfil escolhido', () => {
  abrir()

  const resumo = screen.getByText('O que cada perfil vê').closest('[data-slot="card"]') as HTMLElement
  expect(within(resumo).getByText('Diretoria').nextSibling).toHaveTextContent('Indicadores, Receita e Continuidade')
  expect(within(resumo).getByText('Administrador (TI)').nextSibling).toHaveTextContent(/Fila de inspeção e Usuários$/)

  escolherPerfil('Perdas')
  expect(screen.getByText('Vê Visão 360 e Fila de inspeção.')).toBeInTheDocument()
})
