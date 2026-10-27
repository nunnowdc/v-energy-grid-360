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

const mesesAbreviados = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']

// Competência como vem da Gold: "2025-07" → "jul/2025"
export function formatarCompetencia(competencia: string) {
  const [ano, mes] = competencia.split('-')
  return `${mesesAbreviados[Number(mes) - 1]}/${ano}`
}

// Data como vem da API, sem fuso: "2026-06-21" → "21/06/2026"
export function formatarData(data: string) {
  const [ano, mes, dia] = data.slice(0, 10).split('-')
  return `${dia}/${mes}/${ano}`
}

// Data e hora como vêm da API: "2026-06-12T05:49:00" → "12/06/2026 05:49"
export function formatarDataHora(dataHora: string) {
  return `${formatarData(dataHora)} ${dataHora.slice(11, 16)}`
}

// 203 → "203 kWh"
export function formatarKwh(valor: number) {
  return `${formatarNumero(valor)} kWh`
}

// Competência curta para eixos de gráfico: "2025-07" → "jul/25"
export function formatarCompetenciaCurta(competencia: string) {
  const [ano, mes] = competencia.split('-')
  return `${mesesAbreviados[Number(mes) - 1]}/${ano.slice(2)}`
}
