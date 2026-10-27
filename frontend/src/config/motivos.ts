// Regras da fila de inspeção como a Gold escreve (sem acento) e como a tela mostra.
// Fonte: data-engineering/05_gold_perdas.py, motor de regras do score
const textosMotivos: Record<string, string> = {
  'Queda de consumo >= 50%': 'Queda de consumo ≥ 50%',
  'Queda de consumo >= 30%': 'Queda de consumo ≥ 30%',
  'Queda de consumo >= 15%': 'Queda de consumo ≥ 15%',
  'Medidor eletromecanico': 'Medidor eletromecânico',
  'Leituras estimadas >= 50%': 'Leituras estimadas ≥ 50%',
  'Leituras estimadas >= 25%': 'Leituras estimadas ≥ 25%',
  'Multiplas anomalias de leitura': 'Várias anomalias de leitura',
  'Anomalia de leitura recente': 'Anomalia de leitura recente',
  'Bairro com taxa de irregularidade >= 1.2x': 'Bairro com muita irregularidade',
  'Historico de irregularidade anterior': 'Já teve irregularidade',
  'Inspecionada regular ha <= 180 dias': 'Inspecionada sem irregularidade há até 180 dias',
}

export type Motivo = {
  texto: string
  // Pontos que a regra soma (ou tira) no score, ex.: 40 ou -25
  pontos?: number
}

// "Queda de consumo >= 50% (+40); Medidor eletromecanico (+15)" →
// [{ texto: "Queda de consumo ≥ 50%", pontos: 40 }, { texto: "Medidor eletromecânico", pontos: 15 }]
export function lerMotivos(motivoSuspeita: string): Motivo[] {
  return motivoSuspeita
    .split(';')
    .map((parte) => parte.trim())
    .filter(Boolean)
    .map((parte) => {
      const [, regra = parte, pontos] = /^(.*?)\s*\(([+-]\d+)\)$/.exec(parte) ?? []
      return { texto: textosMotivos[regra] ?? regra, pontos: pontos === undefined ? undefined : Number(pontos) }
    })
}
