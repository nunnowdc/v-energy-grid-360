import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, test } from 'vitest'
import BlocoDados from '@/components/BlocoDados/BlocoDados'
import EstadoConsulta from '@/components/EstadoConsulta/EstadoConsulta'
import { ErroApi } from '@/lib/api/erro-api'
import { renderizar } from '@/test/renderizar'

type BlocoTesteProps = {
  chave: string
  buscar: () => Promise<string[]>
  comVazio?: boolean
}

function BlocoTeste({ chave, buscar, comVazio }: BlocoTesteProps) {
  const consulta = useQuery({ queryKey: [chave], queryFn: buscar, placeholderData: keepPreviousData })

  return (
    <BlocoDados
      titulo="Receita por mês"
      consulta={consulta}
      estaVazio={comVazio ? (dados) => dados.length === 0 : undefined}
    >
      {(dados) => (
        <ul>
          {dados.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </BlocoDados>
  )
}

const nuncaResponde = () => new Promise<string[]>(() => {})

describe('os 4 estados', () => {
  test('carregando: título e esqueleto', () => {
    const { container } = renderizar(<BlocoTeste chave="a" buscar={nuncaResponde} />)
    expect(screen.getByText('Receita por mês')).toBeInTheDocument()
    expect(container.querySelector('[data-slot="skeleton"]')).toBeInTheDocument()
  })

  test('sucesso: os dados chegam ao bloco', async () => {
    renderizar(<BlocoTeste chave="b" buscar={async () => ['jan', 'fev']} />)
    expect(await screen.findByText('fev')).toBeInTheDocument()
  })

  test('vazio: mensagem padrão', async () => {
    renderizar(<BlocoTeste chave="c" buscar={async () => []} comVazio />)
    expect(await screen.findByText('Nenhum dado para os filtros selecionados.')).toBeInTheDocument()
  })

  test('erro: mensagem do backend e "Tentar de novo" busca outra vez', async () => {
    let chamadas = 0
    const buscar = async () => {
      chamadas++
      if (chamadas === 1) {
        throw new ErroApi(404, 'UC não encontrada')
      }
      return ['ok depois']
    }

    renderizar(<BlocoTeste chave="d" buscar={buscar} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('UC não encontrada')

    fireEvent.click(screen.getByRole('button', { name: /Tentar de novo/ }))
    expect(await screen.findByText('ok depois')).toBeInTheDocument()
    expect(chamadas).toBe(2)
  })

  test('erro inesperado (bug) não mostra texto técnico', async () => {
    const buscar = async (): Promise<string[]> => {
      throw new TypeError('x is undefined')
    }

    renderizar(<BlocoTeste chave="e" buscar={buscar} />)
    expect(await screen.findByText('Algo deu errado. Tente de novo em instantes.')).toBeInTheDocument()
    expect(screen.queryByText(/x is undefined/)).not.toBeInTheDocument()
  })

  test('atualizando: dado anterior esmaecido até o novo chegar', async () => {
    let liberar: (dados: string[]) => void = () => {}
    const esperarLiberacao = () =>
      new Promise<string[]>((ok) => {
        liberar = ok
      })

    const { rerender, container } = renderizar(
      <BlocoTeste chave="f1" buscar={async () => ['dado antigo']} />,
    )
    await screen.findByText('dado antigo')

    rerender(<BlocoTeste chave="f2" buscar={esperarLiberacao} />)
    await waitFor(() => expect(container.querySelector('[aria-busy="true"]')).toBeInTheDocument())
    expect(screen.getByText('dado antigo')).toBeInTheDocument()
    expect(container.querySelector('.opacity-50')).toBeInTheDocument()

    await act(async () => liberar(['dado novo']))
    expect(await screen.findByText('dado novo')).toBeInTheDocument()
    expect(container.querySelector('[aria-busy="true"]')).not.toBeInTheDocument()
  })
})

test('aceita um esqueleto próprio (ex.: linha de KPIs)', () => {
  function LinhaKpis() {
    const consulta = useQuery({ queryKey: ['kpis'], queryFn: () => new Promise<number>(() => {}) })
    return (
      <EstadoConsulta consulta={consulta} esqueleto={<p>esqueleto dos KPIs</p>}>
        {(valor) => <p>{valor}</p>}
      </EstadoConsulta>
    )
  }

  renderizar(<LinhaKpis />)
  expect(screen.getByText('esqueleto dos KPIs')).toBeInTheDocument()
})
