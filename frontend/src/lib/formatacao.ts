// Formatos de número usados nas telas, sempre no padrão brasileiro

const moeda = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

const moedaCompacta = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  notation: 'compact',
  maximumFractionDigits: 1,
})

const numero = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 })

const percentualComSinal = new Intl.NumberFormat('pt-BR', {
  style: 'percent',
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
  signDisplay: 'exceptZero',
})

// 412.5 → "R$ 412,50"
export function formatarMoeda(valor: number) {
  return moeda.format(valor)
}

// 169700000 → "R$ 169,7 mi"
export function formatarMoedaCompacta(valor: number) {
  return moedaCompacta.format(valor)
}

// 45000 → "45.000"
export function formatarNumero(valor: number) {
  return numero.format(valor)
}

// Recebe o percentual em pontos, como vem da Gold: 8 → "+8,0%"
export function formatarPercentualComSinal(pontos: number) {
  return percentualComSinal.format(pontos / 100)
}
