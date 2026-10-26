import { fireEvent, render, screen } from '@testing-library/react'
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
