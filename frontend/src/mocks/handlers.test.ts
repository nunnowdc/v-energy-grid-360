import { getResponse } from 'msw'
import { expect, test } from 'vitest'
import { handlers } from '@/mocks/handlers'

function buscar(caminho: string, opcoes?: RequestInit) {
  return getResponse(handlers, new Request(new URL(caminho, location.origin), opcoes))
}

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
