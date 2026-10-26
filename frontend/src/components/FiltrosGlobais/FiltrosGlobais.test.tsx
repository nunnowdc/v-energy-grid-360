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
// Cada filtro é um botão com o rótulo e o valor escolhido, ex.: "Município: Todos"
const campo = (rotulo: string) => screen.getByRole('combobox', { name: new RegExp(`^${rotulo}:`) })
const valorDe = (rotulo: string) => campo(rotulo).getAttribute('aria-label')?.slice(`${rotulo}: `.length)
const abrirLista = (rotulo: string) => fireEvent.click(campo(rotulo))
const fecharLista = () => fireEvent.keyDown(screen.getByRole('listbox'), { key: 'Escape' })
const textos = (rotulo: string) => {
  abrirLista(rotulo)
  const lista = screen.getAllByRole('option').map((opcao) => opcao.textContent)
  fecharLista()
  return lista
}
// Como um clique de verdade: aperta e solta o botão do mouse em cima da opção
const escolher = (rotulo: string, opcao: string) => {
  abrirLista(rotulo)
  const item = screen.getByRole('option', { name: opcao })
  fireEvent.pointerDown(item, { pointerType: 'mouse' })
  fireEvent.click(item)
}

test('mostra só os campos pedidos pela tela', () => {
  abrir('/receita', ['municipio', 'bairro', 'classe'])
  expect(screen.queryByRole('combobox', { name: /^De:/ })).not.toBeInTheDocument()
  expect(campo('Município')).toBeInTheDocument()
  expect(campo('Classe de consumo')).toBeInTheDocument()
})

test('o bairro depende do município, e trocar o município limpa o bairro', () => {
  abrir('/receita', ['municipio', 'bairro', 'classe'])
  expect(campo('Bairro')).toBeDisabled()
  expect(valorDe('Bairro')).toBe('Escolha um município')

  escolher('Município', 'Recife')
  expect(urlAtual()).toBe('?municipio=Recife')
  expect(campo('Bairro')).toBeEnabled()
  expect(textos('Bairro')).toEqual(['Todos', 'Boa Viagem', 'Casa Forte', 'Ibura', 'Pina'])

  escolher('Bairro', 'Pina')
  escolher('Classe de consumo', 'Poder público')
  expect(urlAtual()).toBe('?municipio=Recife&bairro=Pina&classe=PODER_PUBLICO')
  expect(valorDe('Classe de consumo')).toBe('Poder público')

  escolher('Município', 'Olinda')
  expect(urlAtual()).toBe('?municipio=Olinda&classe=PODER_PUBLICO')
})

test('escolher a opção vazia tira o filtro da URL', () => {
  abrir('/receita?classe=RURAL', ['municipio', 'classe'])
  expect(valorDe('Classe de consumo')).toBe('Rural')

  escolher('Classe de consumo', 'Todas')
  expect(urlAtual()).toBe('')
  expect(valorDe('Classe de consumo')).toBe('Todas')
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
  expect(valorDe('De')).toBe('jul/2025')
  expect(textos('De')[1]).toBe('jul/2022')
  expect(valorDe('Até')).toBe('Último mês da base')
  expect(valorDe('Classe de consumo')).toBe('Todas')
  expect(valorDe('Município')).toBe('Todos')
  expect(JSON.parse(screen.getByTestId('filtros').textContent!)).toEqual({ inicio: '2025-07' })

  escolher('Até', 'jan/2024')
  expect(urlAtual()).toContain('inicio=2024-01')
})
