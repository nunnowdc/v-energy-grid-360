import { expect, test } from 'vitest'
import { textoDoCodigo } from '@/config/codigos'

test('categorias da Gold viram texto com acento', () => {
  expect(textoDoCodigo('DANO ELETRICO')).toBe('Dano elétrico')
  expect(textoDoCodigo('GERACAO NA PROPRIA UC')).toBe('Geração na própria UC')
  expect(textoDoCodigo('CONSUMO_ANULADO')).toBe('Consumo anulado')
  expect(textoDoCodigo('WHATSAPP')).toBe('WhatsApp')
})
