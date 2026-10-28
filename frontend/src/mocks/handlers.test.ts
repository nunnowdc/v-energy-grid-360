import { getResponse } from 'msw'
import { expect, test } from 'vitest'
import { handlers } from '@/mocks/handlers'

function buscar(caminho: string, opcoes?: RequestInit) {
  return getResponse(handlers, new Request(new URL(caminho, location.origin), opcoes))
}

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

test('o exemplo de /api/network/continuity: ranking do pior DEC e município só escolhe alimentadores', async () => {
  const corpo = await (await buscar('/api/network/continuity?inicio=2025-07&fim=2026-06&municipio=Olinda'))!.json()

  expect(corpo.periodo_anterior).toEqual({ inicio: '2024-07', fim: '2025-06' })
  // ALM-OLI-002 atende Olinda e Paulista: entra com o DEC do circuito inteiro
  expect(corpo.ranking.map((linha: { alimentador: string }) => linha.alimentador).sort()).toEqual([
    'ALM-OLI-001',
    'ALM-OLI-002',
  ])
  const decs = corpo.ranking.map((linha: { dec: number }) => linha.dec)
  expect(decs).toEqual([...decs].sort((a, b) => b - a))
  expect(corpo.serie.alimentador).toBe(corpo.ranking[0].alimentador)
  expect(corpo.serie.atual).toHaveLength(12)
})

test('a causa filtra só as ocorrências, não o ranking', async () => {
  const todas = await (await buscar('/api/network/continuity?inicio=2026-04&fim=2026-06'))!.json()
  const vegetacao = await (await buscar('/api/network/continuity?inicio=2026-04&fim=2026-06&causa=VEGETACAO'))!.json()

  expect(vegetacao.ranking).toEqual(todas.ranking)
  expect(vegetacao.ocorrencias.por_causa.map((item: { causa: string }) => item.causa)).toEqual(['VEGETACAO'])
  expect(vegetacao.ocorrencias.total).toBeLessThan(todas.ocorrencias.total)
})
