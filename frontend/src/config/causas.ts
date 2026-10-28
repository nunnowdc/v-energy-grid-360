// Causas de interrupção da Gold (fact_ocorrencias.causa) e o nome que aparece na tela.
// "Não informada" (sem registro) e "Não identificada" (apurada sem causa achada) são diferentes
const rotulosCausas: Record<string, string> = {
  CLIMATICA: 'Climática',
  VEGETACAO: 'Vegetação',
  TERCEIROS: 'Terceiros',
  SOBRECARGA: 'Sobrecarga',
  'FALHA DE EQUIPAMENTO': 'Falha de equipamento',
  'NAO IDENTIFICADA': 'Não identificada',
  'NAO INFORMADA': 'Não informada',
}

// Causa nova vinda da Gold aparece com o código, até ganhar um nome aqui
export function rotuloCausa(causa: string) {
  return rotulosCausas[causa] ?? causa
}
