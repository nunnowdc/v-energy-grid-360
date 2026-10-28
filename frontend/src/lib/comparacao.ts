// Variação do período anterior para o atual, em pontos (100 → 108 = 8).
// Sem base de comparação (anterior zero), não existe variação
export function variacaoPercentual(atual: number, anterior: number) {
  return anterior === 0 ? undefined : ((atual - anterior) / anterior) * 100
}
