import { screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import SeloBase from '@/components/SeloBase/SeloBase'
import { opcoesFiltrosExemplo } from '@/mocks/opcoes-filtros'
import { renderizar } from '@/test/renderizar'

test('mostra o primeiro e o último mês da base', () => {
  renderizar(<SeloBase />, { opcoesFiltros: opcoesFiltrosExemplo })
  expect(screen.getByTitle('Período coberto pela base de dados')).toHaveTextContent('Base jul/2022 – jun/2026')
})

test('enquanto as opções não chegam, não mostra nada', () => {
  const { container } = renderizar(<SeloBase />)
  expect(container).toBeEmptyDOMElement()
})
