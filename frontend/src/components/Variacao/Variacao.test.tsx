import { render } from '@testing-library/react'
import { expect, test } from 'vitest'
import Variacao from '@/components/Variacao/Variacao'

const texto = (percentual: number) =>
  render(<Variacao percentual={percentual} complemento="vs. período anterior" />).container.textContent

test.each([
  [8, '▲ +8,0% vs. período anterior'],
  [-6.8, '▼ -6,8% vs. período anterior'],
  [0.05, '▲ +0,1% vs. período anterior'],
  // A seta segue o número arredondado: nunca aparece seta para cima com 0,0%
  [0.04, '▬ 0,0% vs. período anterior'],
  [-0.04, '▬ 0,0% vs. período anterior'],
])('%d mostra "%s"', (percentual, esperado) => {
  expect(texto(percentual)).toBe(esperado)
})
