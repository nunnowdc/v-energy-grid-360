// Variação do período anterior para o atual, em pontos (100 → 108 = 8).
// Sem base de comparação (anterior zero), não existe variação
export function variacaoPercentual(atual: number, anterior: number) {
  return anterior === 0 ? undefined : ((atual - anterior) / anterior) * 100
}

// Para que lado a medida melhora: receita que sobe é boa, DEC que sobe é ruim.
// Medida sem lado bom (ex.: preço médio, consumo de uma UC) não recebe sentido
export type Sentido = 'subir-e-bom' | 'subir-e-ruim'

export type Tom = 'positivo' | 'negativo' | 'neutro'

// Se a variação é boa, ruim ou nenhuma das duas. Quem mostra o número arredondado
// passa o valor já arredondado, para a cor nunca contradizer o "0,0%"
export function tomDaVariacao(variacao: number, sentido?: Sentido): Tom {
  if (!sentido || variacao === 0) {
    return 'neutro'
  }
  const subiu = variacao > 0
  return subiu === (sentido === 'subir-e-bom') ? 'positivo' : 'negativo'
}

// Classe do Tailwind para o texto de cada tom
export const corDoTom: Record<Tom, string> = {
  positivo: 'text-positivo',
  negativo: 'text-negativo',
  neutro: 'text-foreground/75',
}
