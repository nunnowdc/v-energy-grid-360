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
// Período: um botão que abre o calendário de meses, ex.: "Período: jul/2025 – jun/2026"
const botaoPeriodo = (rotulo: string) => screen.getByRole('button', { name: new RegExp(`^${rotulo}:`) })
const periodoDe = (rotulo: string) => botaoPeriodo(rotulo).getAttribute('aria-label')?.slice(`${rotulo}: `.length)
const mes = (nome: string) => screen.getByRole('button', { name: nome })
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

test('alimentador depende do município, e causa aparece com o nome amigável', () => {
  abrir('/continuidade?alimentador=ALM-JAB-002', ['municipio', 'alimentador', 'causa'])
  expect(textos('Alimentador')).toHaveLength(9)

  // ALM-JAB-002 também atende Recife: continua escolhido
  escolher('Município', 'Recife')
  expect(urlAtual()).toBe('?alimentador=ALM-JAB-002&municipio=Recife')
  expect(textos('Alimentador')).toEqual(['Todos', 'ALM-JAB-002', 'ALM-REC-001', 'ALM-REC-002', 'ALM-REC-003'])

  // Olinda não é atendida por ele: sai da URL
  escolher('Município', 'Olinda')
  expect(urlAtual()).toBe('?municipio=Olinda')

  escolher('Causa', 'Falha de equipamento')
  expect(urlAtual()).toBe('?municipio=Olinda&causa=FALHA+DE+EQUIPAMENTO')
})

test('período: o calendário escolhe o primeiro e o último mês', () => {
  abrir('/', ['periodo'])
  expect(periodoDe('Período')).toBe('jul/2025 – jun/2026')

  fireEvent.click(botaoPeriodo('Período'))
  fireEvent.click(mes('jan/2025'))
  expect(screen.getByText('Começa em jan/2025. Agora clique no último mês.')).toBeInTheDocument()
  fireEvent.click(mes('jun/2025'))
  expect(urlAtual()).toBe('?de=2025-01&ate=2025-06')
  expect(periodoDe('Período')).toBe('jan/2025 – jun/2025')
})

test('período: meses sem o período anterior na base ficam apagados', () => {
  abrir('/', ['periodo'])
  fireEvent.click(botaoPeriodo('Período'))
  fireEvent.click(screen.getByRole('button', { name: 'Ano anterior' }))
  fireEvent.click(screen.getByRole('button', { name: 'Ano anterior' }))
  fireEvent.click(screen.getByRole('button', { name: 'Ano anterior' }))
  // Em 2022, julho é o primeiro mês da base: não há mês antes dele para comparar
  expect(mes('jul/2022')).toBeDisabled()
  expect(mes('ago/2022')).toBeEnabled()
  expect(mes('jun/2022')).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Ano anterior' })).toBeDisabled()
})

test('período: o atalho do padrão tira o filtro da URL, e valores inválidos da URL são ignorados', () => {
  abrir('/?de=2022-07&ate=2022-09&classe=INVENTADA&municipio=Narnia', ['periodo', 'municipio', 'classe'])
  expect(periodoDe('Período')).toBe('jul/2025 – jun/2026')
  expect(valorDe('Município')).toBe('Todos')
  expect(JSON.parse(screen.getByTestId('filtros').textContent!)).toEqual({})

  fireEvent.click(botaoPeriodo('Período'))
  fireEvent.click(screen.getByRole('button', { name: 'Ano de 2024' }))
  expect(urlAtual()).toContain('de=2024-01&ate=2024-12')

  fireEvent.click(botaoPeriodo('Período'))
  fireEvent.click(screen.getByRole('button', { name: 'Últimos 12 meses' }))
  expect(urlAtual()).not.toContain('de=')
})

test('Receita: escolher o base leva o comparado para os mesmos meses, com o mesmo tamanho', () => {
  abrir('/receita', ['comparacao'])
  expect(periodoDe('Período base')).toBe('jul/2022 – jun/2023')
  expect(periodoDe('Comparado com')).toBe('jul/2025 – jun/2026')

  fireEvent.click(botaoPeriodo('Período base'))
  fireEvent.click(screen.getByRole('button', { name: 'Próximo ano' }))
  fireEvent.click(mes('jan/2023'))
  fireEvent.click(mes('mar/2023'))
  expect(urlAtual()).toBe('?base_de=2023-01&base_ate=2023-03')
  expect(periodoDe('Comparado com')).toBe('jan/2026 – mar/2026')
})

test('Receita: no comparado, um clique escolhe o começo e o tamanho vem do base', () => {
  abrir('/receita?base_de=2023-01&base_ate=2023-03', ['comparacao'])

  fireEvent.click(botaoPeriodo('Comparado com'))
  expect(screen.getByText('Clique no primeiro mês: o período tem 3 meses, como o base.')).toBeInTheDocument()
  // Abre no ano do comparado em vigor (2026); jul/2025 fica um ano antes
  fireEvent.click(screen.getByRole('button', { name: 'Ano anterior' }))
  fireEvent.click(mes('jul/2025'))
  expect(urlAtual()).toBe('?base_de=2023-01&base_ate=2023-03&comparado_de=2025-07')
  expect(periodoDe('Comparado com')).toBe('jul/2025 – set/2025')

  // Os atalhos são os mesmos meses do base nos anos seguintes; o último é o padrão e sai da URL
  fireEvent.click(botaoPeriodo('Comparado com'))
  fireEvent.click(screen.getByRole('button', { name: 'jan/2026 – mar/2026' }))
  expect(urlAtual()).toBe('?base_de=2023-01&base_ate=2023-03')
})
