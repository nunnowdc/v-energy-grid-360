import { getResponse } from 'msw'
import { expect, test } from 'vitest'
import { handlers } from '@/mocks/handlers'

function buscar(caminho: string) {
  return getResponse(handlers, new Request(new URL(caminho, location.origin)))
}

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
