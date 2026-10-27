import { getResponse } from 'msw'
import { beforeEach, expect, test } from 'vitest'
import { handlers } from '@/mocks/handlers'
import { limparOrdens } from '@/mocks/inspecoes'

function buscar(caminho: string, opcoes?: RequestInit) {
  return getResponse(handlers, new Request(new URL(caminho, location.origin), opcoes))
}

const enviar = (metodo: string, caminho: string, corpo?: unknown) =>
  buscar(caminho, {
    method: metodo,
    headers: { 'Content-Type': 'application/json' },
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
  })

beforeEach(() => {
  limparOrdens()
})

test('o exemplo de /api/filters/options cobre os 48 meses da base', async () => {
  const resposta = await buscar('/api/filters/options')
  const corpo = await resposta!.json()

  expect(corpo.competencias).toHaveLength(48)
  expect(corpo.competencias[0]).toBe('2022-07')
  expect(corpo.competencias.at(-1)).toBe('2026-06')
  expect(Object.keys(corpo)).toEqual(['competencias', 'municipios', 'classes', 'alimentadores', 'causas'])
})

test('o exemplo de /api/metrics/general compara com o período anterior de mesmo tamanho', async () => {
  const resposta = await buscar('/api/metrics/general?inicio=2025-07&fim=2026-06')
  const corpo = await resposta!.json()

  expect(corpo.atual).toMatchObject({ inicio: '2025-07', fim: '2026-06' })
  expect(corpo.anterior).toMatchObject({ inicio: '2024-07', fim: '2025-06' })
  expect(corpo.mensal.atual).toHaveLength(12)
  expect(corpo.mensal.anterior).toHaveLength(12)
  expect(corpo.por_classe).toHaveLength(5)
})

test('filtrar por classe deixa só essa classe', async () => {
  const resposta = await buscar('/api/metrics/general?inicio=2026-04&fim=2026-06&municipio=Olinda&classe=RURAL')
  const corpo = await resposta!.json()

  expect(corpo.por_classe.map((linha: { classe: string }) => linha.classe)).toEqual(['RURAL'])
  expect(corpo.anterior).toMatchObject({ inicio: '2026-01', fim: '2026-03' })
})

test('período fora de 3, 6 ou 12 meses responde 422', async () => {
  const resposta = await buscar('/api/metrics/general?inicio=2026-02&fim=2026-06')
  expect(resposta!.status).toBe(422)
})

test('o exemplo de /api/metrics/revenue-variance usa os períodos fixos e fecha a conta', async () => {
  const resposta = await buscar('/api/metrics/revenue-variance')
  const corpo = await resposta!.json()

  expect(corpo.periodo_p0).toEqual({ inicio: '2022-07', fim: '2023-06' })
  expect(corpo.periodo_p1).toEqual({ inicio: '2025-07', fim: '2026-06' })
  const { receita_p0, receita_p1, efeito_volume, efeito_preco } = corpo.total
  expect(efeito_volume + efeito_preco).toBeCloseTo(receita_p1 - receita_p0)
  expect(corpo.detalhamento.nivel).toBe('municipio')
  expect(corpo.por_gd).toHaveLength(2)
})

test('cada filtro desce um nível no detalhamento', async () => {
  const doMunicipio = await (await buscar('/api/metrics/revenue-variance?municipio=Olinda'))!.json()
  expect(doMunicipio.detalhamento.nivel).toBe('bairro')
  expect(doMunicipio.detalhamento.linhas.map((linha: { nome: string }) => linha.nome)).toEqual([
    'Bairro Novo',
    'Casa Caiada',
    'Rio Doce',
  ])

  const doBairro = await (await buscar('/api/metrics/revenue-variance?municipio=Olinda&bairro=Rio+Doce'))!.json()
  expect(doBairro.detalhamento.nivel).toBe('classe')
})

test('a fila de exemplo vem na ordem da prioridade, paginada', async () => {
  const corpo = await (await buscar('/api/inspections/queue?pagina=2&limite=10'))!.json()

  expect(corpo.itens).toHaveLength(10)
  expect(corpo.itens[0].prioridade).toBe(11)
  expect(corpo.total).toBe(corpo.resumo.ucs)
  const scores = corpo.itens.map((item: { score: number }) => item.score)
  expect(scores).toEqual([...scores].sort((a, b) => b - a))
  expect(Math.min(...scores)).toBeGreaterThanOrEqual(20)
})

test('gerar a ordem marca a UC na fila e a ordem segue aberta → em campo → concluída', async () => {
  const fila = await (await buscar('/api/inspections/queue?limite=1'))!.json()
  const idUc = fila.itens[0].id_uc

  const criadas = await (await enviar('POST', '/api/inspections/order', { ids_uc: [idUc, idUc] }))!.json()
  expect(criadas.ordens).toHaveLength(1)
  const { id_ordem } = criadas.ordens[0]

  const depois = await (await buscar('/api/inspections/queue?limite=1'))!.json()
  expect(depois.itens[0].ordem_aberta).toEqual({ id_ordem, status: 'ABERTA' })

  // Não dá para concluir sem passar pelo campo
  const pulando = await enviar('PATCH', `/api/inspections/${id_ordem}`, {
    status: 'CONCLUIDA',
    resultado: 'SEM_IRREGULARIDADE',
  })
  expect(pulando!.status).toBe(409)

  await enviar('PATCH', `/api/inspections/${id_ordem}`, { status: 'EM_CAMPO' })
  const concluida = await (
    await enviar('PATCH', `/api/inspections/${id_ordem}`, { status: 'CONCLUIDA', resultado: 'IRREGULARIDADE_CONFIRMADA' })
  )!.json()
  expect(concluida).toMatchObject({ status: 'CONCLUIDA', resultado: 'IRREGULARIDADE_CONFIRMADA' })

  const ordens = await (await buscar('/api/inspections/orders'))!.json()
  expect(ordens.itens).toHaveLength(1)
})

test('cancelar guarda a ordem como cancelada', async () => {
  const fila = await (await buscar('/api/inspections/queue?limite=1'))!.json()
  const criadas = await (await enviar('POST', '/api/inspections/order', { ids_uc: [fila.itens[0].id_uc] }))!.json()

  const cancelada = await (await enviar('DELETE', `/api/inspections/${criadas.ordens[0].id_ordem}`))!.json()
  expect(cancelada.status).toBe('CANCELADA')
})
