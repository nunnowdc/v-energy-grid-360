import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import FiltroSelect from '@/components/FiltroSelect/FiltroSelect'

const opcoes = [
  { valor: 'JABOATAO', rotulo: 'Jaboatão dos Guararapes' },
  { valor: 'RECIFE', rotulo: 'Recife' },
]

test('o botão inteiro abre a lista, com a opção vazia primeiro', () => {
  render(<FiltroSelect rotulo="Município" opcoes={opcoes} textoVazio="Todos" aoMudar={vi.fn()} />)
  fireEvent.click(screen.getByRole('combobox', { name: 'Município: Todos' }))

  const lista = screen.getAllByRole('option').map((opcao) => opcao.textContent)
  expect(lista).toEqual(['Todos', 'Jaboatão dos Guararapes', 'Recife'])
})

test('valor longo aparece inteiro ao passar o mouse', () => {
  render(<FiltroSelect rotulo="Município" valor="JABOATAO" opcoes={opcoes} textoVazio="Todos" aoMudar={vi.fn()} />)
  expect(screen.getByRole('combobox')).toHaveAttribute('title', 'Município: Jaboatão dos Guararapes')
})

test('desabilitado, não abre a lista', () => {
  render(<FiltroSelect rotulo="Bairro" opcoes={[]} textoVazio="Escolha um município" desabilitado aoMudar={vi.fn()} />)
  fireEvent.click(screen.getByRole('combobox'))
  expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
})

// Lista longa, como os bairros do Recife
const bairros = [
  'Afogados', 'Boa Viagem', 'Boa Vista', 'Casa Amarela', 'Casa Forte', 'Graças',
  'Ibura', 'Macaxeira', 'Pina', 'São José', 'Torre', 'Várzea',
].map((nome) => ({ valor: nome, rotulo: nome }))

test('lista com mais de 10 opções ganha busca, que ignora acento e maiúscula', async () => {
  const aoMudar = vi.fn()
  render(<FiltroSelect rotulo="Bairro" opcoes={bairros} textoVazio="Todos" aoMudar={aoMudar} />)
  fireEvent.click(screen.getByRole('combobox', { name: 'Bairro: Todos' }))

  const busca = await screen.findByRole('combobox', { name: 'Buscar bairro' })
  expect(screen.getAllByRole('option')).toHaveLength(13)
  fireEvent.change(busca, { target: { value: 'varzea' } })

  await waitFor(() => expect(screen.getAllByRole('option').map((opcao) => opcao.textContent)).toEqual(['Várzea']))
  fireEvent.click(screen.getByRole('option', { name: 'Várzea' }))
  expect(aoMudar).toHaveBeenCalledWith('Várzea')
})

test('na lista com busca, "Todos" tira o filtro', async () => {
  const aoMudar = vi.fn()
  render(<FiltroSelect rotulo="Bairro" valor="Pina" opcoes={bairros} textoVazio="Todos" aoMudar={aoMudar} />)
  fireEvent.click(screen.getByRole('combobox', { name: 'Bairro: Pina' }))

  fireEvent.click(await screen.findByRole('option', { name: 'Todos' }))
  expect(aoMudar).toHaveBeenCalledWith(undefined)
})

test('busca sem resultado avisa', async () => {
  render(<FiltroSelect rotulo="Bairro" opcoes={bairros} textoVazio="Todos" aoMudar={vi.fn()} />)
  fireEvent.click(screen.getByRole('combobox', { name: 'Bairro: Todos' }))

  fireEvent.change(await screen.findByRole('combobox', { name: 'Buscar bairro' }), { target: { value: 'xyz' } })
  expect(await screen.findByText('Nada encontrado.')).toBeInTheDocument()
})
