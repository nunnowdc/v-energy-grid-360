import { NO_RECUSA } from '@/config/nos-agente'

// concluido: seguiu o caminho normal; atencao: algo falhou ou não achou, mas o
// agente continuou; interrompido: o caminho termina em recusa
export type SituacaoPasso = 'concluido' | 'atencao' | 'interrompido'

export type PassoAgente = {
  // Número do nó no grafo do agente; null quando o texto não segue o padrão
  no: number | null
  // Cada nó pode registrar mais de uma linha (ex.: a síntese e a conferência)
  detalhes: string[]
  situacao: SituacaoPasso
  // O agente voltou a um nó anterior (nova tentativa de SQL)
  repeticao: boolean
}

const PREFIXO_NO = /^Nó (\d+)\s*[—-]\s*/
// Rótulo curto antes dos dois-pontos ("Filtro de segurança: aprovado."), que
// repete o nome do nó; rótulos com parênteses ou ponto têm informação e ficam
const ROTULO_REPETIDO = /^[^:().]{1,30}:\s+/

const SINAIS_INTERRUPCAO = /bloquead|fora \(|reprovado por heur|clima sem termo|'recusa'/i
const SINAIS_ATENCAO = /reprovad|erro|miss|indispon|0 chunk|sem linhas/i

// A auditoria guarda os passos como texto JSON; aceita também a lista pronta
export function lerListaPassos(passos: string | string[] | null | undefined): string[] {
  if (Array.isArray(passos)) {
    return passos
  }
  if (!passos) {
    return []
  }
  try {
    const lista: unknown = JSON.parse(passos)
    return Array.isArray(lista) ? lista.map(String) : []
  } catch {
    return []
  }
}

function situacaoDo(no: number | null, detalhes: string[]): SituacaoPasso {
  const texto = detalhes.join(' ')
  if (no === null || no === NO_RECUSA || SINAIS_INTERRUPCAO.test(texto)) {
    return 'interrompido'
  }
  return SINAIS_ATENCAO.test(texto) ? 'atencao' : 'concluido'
}

const comMaiuscula = (texto: string) => texto.charAt(0).toUpperCase() + texto.slice(1)

// Junta linhas seguidas do mesmo nó e marca quando o agente volta a um nó
// anterior: o caminho percorrido vira uma lista de passos na ordem
export function montarPassos(passos: string[]): PassoAgente[] {
  const grupos: { no: number | null; detalhes: string[] }[] = []

  for (const passo of passos) {
    const prefixo = PREFIXO_NO.exec(passo)
    const no = prefixo ? Number(prefixo[1]) : null
    const detalhe = comMaiuscula(passo.slice(prefixo?.[0].length ?? 0).replace(ROTULO_REPETIDO, '').trim())
    const ultimo = grupos.at(-1)

    if (ultimo && no !== null && ultimo.no === no) {
      ultimo.detalhes.push(detalhe)
    } else {
      grupos.push({ no, detalhes: [detalhe] })
    }
  }

  const vistos = new Set<number>()
  return grupos.map(({ no, detalhes }) => {
    const repeticao = no !== null && vistos.has(no)
    if (no !== null) {
      vistos.add(no)
    }
    return { no, detalhes, situacao: situacaoDo(no, detalhes), repeticao }
  })
}
