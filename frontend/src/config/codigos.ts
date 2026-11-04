// A Gold guarda categorias em maiúsculas e sem acento (ex.: "DANO ELETRICO").
// Aqui elas viram texto de tela: "Dano elétrico"
const palavrasComAcento: Record<string, string> = {
  APOS: 'após',
  CONTESTACAO: 'contestação',
  CREDITOS: 'créditos',
  DISTRIBUIDA: 'distribuída',
  ELETRICO: 'elétrico',
  ELETROMECANICO: 'eletromecânico',
  ELETRONICO: 'eletrônico',
  GERACAO: 'geração',
  HOMOLOGACAO: 'homologação',
  INTERRUPCAO: 'interrupção',
  LIGACAO: 'ligação',
  OSCILACAO: 'oscilação',
  PROPRIA: 'própria',
  RELIGACAO: 'religação',
  SOLICITACAO: 'solicitação',
}

// Siglas e marcas mantêm a grafia própria
const palavrasFixas: Record<string, string> = {
  APP: 'App',
  UC: 'UC',
  WHATSAPP: 'WhatsApp',
}

export function textoDoCodigo(codigo: string) {
  const palavras = codigo
    .split(/[\s_]+/)
    .filter(Boolean)
    .map((palavra) => palavrasFixas[palavra] ?? palavrasComAcento[palavra] ?? palavra.toLowerCase())
  const texto = palavras.join(' ')
  return texto.charAt(0).toUpperCase() + texto.slice(1)
}
