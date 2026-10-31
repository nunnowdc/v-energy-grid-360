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

const dataHoraRecife = new Intl.DateTimeFormat('pt-BR', {
  timeZone: 'America/Recife',
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

// Instante com fuso, como o backend grava as ordens, no horário de Recife
// (qualquer que seja o fuso do computador): "2026-10-28T21:09:39.757316Z" → "28/10/2026 18:09"
export function formatarInstante(instante: string) {
  return dataHoraRecife.format(new Date(instante)).replace(',', '')
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

// Energia na maior unidade que deixa o número curto: 19.450.000 → "19,5 GWh"
export function formatarEnergia(kwh: number) {
  if (Math.abs(kwh) >= 1_000_000) {
    return `${formatarNumero(kwh / 1_000_000)} GWh`
  }
  if (Math.abs(kwh) >= 1_000) {
    return `${formatarNumero(kwh / 1_000)} MWh`
  }
  return formatarKwh(kwh)
}

// Intervalo de competências: ("2025-07", "2026-06") → "jul/2025 – jun/2026"
export function formatarPeriodo(inicio: string, fim: string) {
  return `${formatarCompetencia(inicio)} – ${formatarCompetencia(fim)}`
}

const moedaCompactaComSinal = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  notation: 'compact',
  maximumFractionDigits: 1,
  signDisplay: 'exceptZero',
})

// Diferença em reais, sempre com sinal: 22500000 → "+R$ 22,5 mi"
export function formatarMoedaCompactaComSinal(valor: number) {
  return moedaCompactaComSinal.format(valor)
}
