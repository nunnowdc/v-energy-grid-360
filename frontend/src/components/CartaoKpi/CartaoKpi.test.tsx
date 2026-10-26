import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import CartaoKpi from '@/components/CartaoKpi/CartaoKpi'

test('mostra título, valor, variação e detalhe', () => {
  render(
    <CartaoKpi
      titulo="Receita faturada"
      valor="R$ 169,7 mi"
      variacao={8}
      complementoVariacao="vs. período anterior"
      detalhe="jul/25 – jun/26"
    />,
  )

  expect(screen.getByText('Receita faturada')).toBeInTheDocument()
  expect(screen.getByText('R$ 169,7 mi')).toBeInTheDocument()
  expect(screen.getByText('+8,0%', { exact: false })).toBeInTheDocument()
  expect(screen.getByText('jul/25 – jun/26')).toBeInTheDocument()
})

test('sem variação, não mostra seta', () => {
  const { container } = render(<CartaoKpi titulo="UCs ativas" valor="45.000" />)
  expect(container.textContent).not.toMatch(/[▲▼▬]/)
})
