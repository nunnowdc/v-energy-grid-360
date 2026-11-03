import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import Variacao from '@/components/Variacao/Variacao'
import type { Sentido } from '@/lib/comparacao'

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

test.each([
  [8, 'subir-e-bom', 'text-positivo', '(melhora)'],
  [-8, 'subir-e-bom', 'text-negativo', '(piora)'],
  // DEC, FEC e atrasos: subir é ruim
  [8, 'subir-e-ruim', 'text-negativo', '(piora)'],
  [-8, 'subir-e-ruim', 'text-positivo', '(melhora)'],
] as const)('%d com sentido %s fica com %s e avisa %s', (percentual, sentido: Sentido, classe, aviso) => {
  render(<Variacao percentual={percentual} sentido={sentido} />)

  expect(screen.getByText(aviso).parentElement).toHaveClass(classe)
})

test('0,0% fica sem cor, mesmo com sentido', () => {
  render(<Variacao percentual={0.04} sentido="subir-e-bom" />)

  expect(screen.getByText('0,0%', { exact: false })).toHaveClass('text-foreground/75')
})
