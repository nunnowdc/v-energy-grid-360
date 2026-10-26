import { fireEvent, screen } from '@testing-library/react'
import { useLocation } from 'react-router'
import { expect, test } from 'vitest'
import FiltrosGlobais, { type CampoFiltro } from '@/components/FiltrosGlobais/FiltrosGlobais'
import { useFiltros } from '@/hooks/use-filtros'
import { opcoesFiltrosExemplo } from '@/mocks/opcoes-filtros'
import { renderizar } from '@/test/renderizar'

// Mostra a URL atual e os filtros que as telas receberiam
function Espiao() {
  const { search } = useLocation()
  const { filtros } = useFiltros()
  return (
    <>
      <output data-testid="url">{decodeURIComponent(search)}</output>
      <output data-testid="filtros">{JSON.stringify(filtros)}</output>
    </>
  )
}

function abrir(url: string, campos: CampoFiltro[]) {
  renderizar(
    <>
      <FiltrosGlobais campos={campos} />
      <Espiao />
    </>,
    { url, opcoesFiltros: opcoesFiltrosExemplo },
  )
}

const urlAtual = () => screen.getByTestId('url').textContent
const campo = (rotulo: string) => screen.getByLabelText(rotulo) as HTMLSelectElement
const textos = (select: HTMLSelectElement) => [...select.options].map((opcao) => opcao.text)
const escolher = (rotulo: string, valor: string) =>
  fireEvent.change(campo(rotulo), { target: { value: valor } })

test('mostra só os campos pedidos pela tela', () => {
  abrir('/receita', ['municipio', 'bairro', 'classe'])
  expect(screen.queryByLabelText('De')).not.toBeInTheDocument()
  expect(campo('Município')).toBeInTheDocument()
  expect(campo('Classe de consumo')).toBeInTheDocument()
})

test('o bairro depende do município, e trocar o município limpa o bairro', () => {
  abrir('/receita', ['municipio', 'bairro', 'classe'])
  expect(campo('Bairro')).toBeDisabled()
  expect(textos(campo('Bairro'))[0]).toBe('Escolha um município')

  escolher('Município', 'Recife')
  expect(urlAtual()).toBe('?municipio=Recife')
  expect(campo('Bairro')).toBeEnabled()
  expect(textos(campo('Bairro'))).toEqual(['Todos', 'Boa Viagem', 'Casa Forte', 'Ibura', 'Pina'])

  escolher('Bairro', 'Pina')
  escolher('Classe de consumo', 'PODER_PUBLICO')
  expect(urlAtual()).toBe('?municipio=Recife&bairro=Pina&classe=PODER_PUBLICO')
  expect(textos(campo('Classe de consumo'))).toContain('Poder público')

  escolher('Município', 'Olinda')
  expect(urlAtual()).toBe('?municipio=Olinda&classe=PODER_PUBLICO')
})

test('"Limpar filtros" só ativa quando há filtro e limpa a URL', () => {
  abrir('/receita?classe=RURAL', ['municipio', 'classe'])
  const limpar = screen.getByRole('button', { name: /Limpar filtros/ })
  expect(limpar).toBeEnabled()

  fireEvent.click(limpar)
  expect(urlAtual()).toBe('')
  expect(limpar).toBeDisabled()
})

test('período com os meses da base e valores inválidos da URL ignorados', () => {
  abrir('/?inicio=2025-07&classe=INVENTADA&municipio=Narnia', ['periodo', 'municipio', 'classe'])
  expect(campo('De')).toHaveValue('2025-07')
  expect(textos(campo('De'))[1]).toBe('jul/2022')
  expect(textos(campo('Até'))[0]).toBe('Último mês da base')
  expect(campo('Classe de consumo')).toHaveValue('')
  expect(campo('Município')).toHaveValue('')
  expect(JSON.parse(screen.getByTestId('filtros').textContent!)).toEqual({ inicio: '2025-07' })

  escolher('Até', '2024-01')
  expect(urlAtual()).toContain('inicio=2024-01')
})
