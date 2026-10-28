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

test('período: últimos 12 meses por padrão, e valores inválidos da URL ignorados', () => {
  abrir('/?meses=5&classe=INVENTADA&municipio=Narnia', ['periodo', 'municipio', 'classe'])
  expect(valorDe('Período')).toBe('Últimos 12 meses')
  expect(textos('Período')).toEqual(['Últimos 12 meses', 'Últimos 6 meses', 'Últimos 3 meses'])
  expect(valorDe('Classe de consumo')).toBe('Todas')
  expect(valorDe('Município')).toBe('Todos')
  expect(JSON.parse(screen.getByTestId('filtros').textContent!)).toEqual({})

  escolher('Período', 'Últimos 3 meses')
  expect(urlAtual()).toContain('meses=3')
})

test('alimentador depende do município, e causa aparece com o nome amigável', () => {
  abrir('/continuidade?alimentador=ALM-JAB-002', ['periodo', 'municipio', 'alimentador', 'causa'])
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

test('"Até" lista só os meses com espaço para o período anterior, do mais recente ao mais antigo', () => {
  abrir('/?meses=12', ['periodo', 'ate'])
  expect(valorDe('Período')).toBe('Últimos 12 meses')
  expect(valorDe('Até')).toBe('jun/2026')
  const meses = textos('Até')
  expect(meses.slice(0, 3)).toEqual(['jun/2026', 'mai/2026', 'abr/2026'])
  expect(meses.at(-1)).toBe('jun/2024')

  escolher('Até', 'dez/2025')
  expect(urlAtual()).toBe('?meses=12&ate=2025-12')
})

test('anos da Receita: cada lista só deixa o comparado depois do base', () => {
  abrir('/receita', ['anos'])
  expect(valorDe('Período base')).toBe('jul/2022 – jun/2023')
  expect(valorDe('Comparado com')).toBe('jul/2025 – jun/2026')
  expect(textos('Período base')).toEqual(['jul/2022 – jun/2023', 'jul/2023 – jun/2024', 'jul/2024 – jun/2025'])

  escolher('Período base', 'jul/2024 – jun/2025')
  expect(urlAtual()).toBe('?base=2024-07')
  // Com o base em jul/2024, o comparado só pode ser o último ano
  expect(textos('Comparado com')).toEqual(['jul/2025 – jun/2026'])

  escolher('Período base', 'jul/2022 – jun/2023')
  escolher('Comparado com', 'jul/2023 – jun/2024')
  expect(urlAtual()).toBe('?comparado=2023-07')
  expect(textos('Período base')).toEqual(['jul/2022 – jun/2023'])
})
