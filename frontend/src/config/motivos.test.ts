import { expect, test } from 'vitest'
import { lerMotivos } from '@/config/motivos'

test('separa as regras e os pontos de cada uma', () => {
  expect(lerMotivos('Queda de consumo >= 50% (+40); Inspecionada regular ha <= 180 dias (-25)')).toEqual([
    { texto: 'Queda de consumo ≥ 50%', pontos: 40 },
    { texto: 'Inspecionada sem irregularidade há até 180 dias', pontos: -25 },
  ])
})

test('regra desconhecida aparece como veio', () => {
  expect(lerMotivos('Regra nova')).toEqual([{ texto: 'Regra nova', pontos: undefined }])
  expect(lerMotivos('')).toEqual([])
})
