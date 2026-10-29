import { formatarPeriodo } from '@/lib/formatacao'

// Períodos escolhidos nos filtros: intervalos de meses (yyyy-MM) dentro da base.
// As telas comparam um período base com um período comparado, de mesmo tamanho,
// que começa depois do fim do base

export type Periodo = { de: string; ate: string }

export type AtalhoPeriodo = { rotulo: string; periodo: Periodo }

// Comparação sem escolha: a Receita responde à pergunta do case (primeiro ano da
// base × último ano); Indicadores e Continuidade mostram o último ano contra o anterior
export type PadraoComparacao = 'inicio-da-base' | 'ano-anterior'

// Com o outro período ao lado, até 24 meses cabem nos 48 meses da base
const MAXIMO_MESES = 24
const MESES_PADRAO = 12

const posicoes = (competencias: string[], { de, ate }: Periodo) => {
  const inicio = competencias.indexOf(de)
  const fim = competencias.indexOf(ate)
  return { inicio, fim, tamanho: fim - inicio + 1 }
}

export const tamanhoDoPeriodo = (competencias: string[], periodo: Periodo) => posicoes(competencias, periodo).tamanho

// N meses a partir de "de"; undefined se passar do fim da base
export function periodoDeTamanho(competencias: string[], de: string, tamanho: number): Periodo | undefined {
  const inicio = competencias.indexOf(de)
  const ate = competencias[inicio + tamanho - 1]
  return inicio >= 0 && ate ? { de, ate } : undefined
}

// Mesmos meses do ano dos dois lados (jan–mar × jan–mar): sem efeito da estação
export const mesmosMesesDoAno = (a: Periodo, b: Periodo) => a.de.slice(5) === b.de.slice(5)

// De 1 a 24 meses, e depois dele precisa caber o comparado, de mesmo tamanho
export function baseValida(competencias: string[], base: Periodo) {
  const { inicio, fim, tamanho } = posicoes(competencias, base)
  return inicio >= 0 && fim >= inicio && tamanho <= MAXIMO_MESES && fim + tamanho <= competencias.length - 1
}

// O comparado começa depois do fim do base e cabe na base
export function comparadoValido(competencias: string[], base: Periodo, de: string) {
  const { fim, tamanho } = posicoes(competencias, base)
  const inicio = competencias.indexOf(de)
  return inicio > fim && inicio + tamanho - 1 <= competencias.length - 1
}

export function basePadrao(competencias: string[], padrao: PadraoComparacao): Periodo | undefined {
  // Primeiro ano da base, ou os 12 meses antes dos últimos 12
  const de = padrao === 'inicio-da-base' ? competencias[0] : competencias.at(-2 * MESES_PADRAO)
  const base = de ? periodoDeTamanho(competencias, de, MESES_PADRAO) : undefined
  return base && baseValida(competencias, base) ? base : undefined
}

// Os comparados com os mesmos meses do ano do base, do mais antigo ao mais recente
function comparadosComMesmosMeses(competencias: string[], base: Periodo): Periodo[] {
  const { inicio, tamanho } = posicoes(competencias, base)
  const comparados: Periodo[] = []
  for (let posicao = inicio + 12; posicao < competencias.length; posicao += 12) {
    const comparado = periodoDeTamanho(competencias, competencias[posicao], tamanho)
    if (comparado && comparadoValido(competencias, base, comparado.de)) {
      comparados.push(comparado)
    }
  }
  return comparados
}

// Os mesmos meses do ano no ano mais recente que cabe; sem isso, os últimos meses da base
export function comparadoPadrao(competencias: string[], base: Periodo): Periodo | undefined {
  const mesmosMeses = comparadosComMesmosMeses(competencias, base).at(-1)
  if (mesmosMeses) {
    return mesmosMeses
  }
  const tamanho = tamanhoDoPeriodo(competencias, base)
  const ultimos = periodoDeTamanho(competencias, competencias.at(-tamanho) ?? '', tamanho)
  return ultimos && comparadoValido(competencias, base, ultimos.de) ? ultimos : undefined
}

// O período cortado aos meses da base ("2026" vira jan–jun/2026); undefined se
// nenhum mês dele está na base
export function dentroDaBase(competencias: string[], { de, ate }: Periodo): Periodo | undefined {
  const primeiro = competencias[0]
  const ultimo = competencias.at(-1)
  if (!primeiro || !ultimo) {
    return undefined
  }
  const inicio = de < primeiro ? primeiro : de
  const fim = ate > ultimo ? ultimo : ate
  return inicio <= fim && competencias.includes(inicio) && competencias.includes(fim)
    ? { de: inicio, ate: fim }
    : undefined
}

// Um período consultado (ex.: pelo agente) vira o comparado, que é o que os KPIs
// mostram. O base é o informado ou, sem ele, os mesmos meses um ano antes; sem
// espaço para isso, os meses logo antes. undefined quando nenhum cabe
export function comparacaoDoPeriodo(
  competencias: string[],
  periodo: Periodo,
  base?: Periodo,
): { base: Periodo; comparado: Periodo } | undefined {
  const comparado = dentroDaBase(competencias, periodo)
  if (!comparado) {
    return undefined
  }
  const { inicio, tamanho } = posicoes(competencias, comparado)
  const candidatos = [
    base && dentroDaBase(competencias, base),
    periodoDeTamanho(competencias, competencias[inicio - 12] ?? '', tamanho),
    periodoDeTamanho(competencias, competencias[inicio - tamanho] ?? '', tamanho),
  ]
  const escolhido = candidatos.find(
    (candidato) =>
      candidato &&
      tamanhoDoPeriodo(competencias, candidato) === tamanho &&
      baseValida(competencias, candidato) &&
      comparadoValido(competencias, candidato, comparado.de),
  )
  return escolhido ? { base: escolhido, comparado } : undefined
}

export function atalhosDaBase(competencias: string[]): AtalhoPeriodo[] {
  // Anos de 12 meses no ritmo da base (jul–jun), contados do primeiro mês
  const anosDaBase = competencias
    .filter((_, posicao) => posicao % 12 === 0)
    .map((de) => periodoDeTamanho(competencias, de, 12))
    .filter((periodo) => periodo !== undefined)
    .map((periodo) => ({ rotulo: formatarPeriodo(periodo.de, periodo.ate), periodo }))
  const anosCivis = anosCompletos(competencias).map((ano) => ({
    rotulo: `Ano de ${ano}`,
    periodo: { de: `${ano}-01`, ate: `${ano}-12` },
  }))
  return [...anosDaBase, ...anosCivis].filter(({ periodo }) => baseValida(competencias, periodo))
}

export const atalhosDoComparado = (competencias: string[], base: Periodo): AtalhoPeriodo[] =>
  comparadosComMesmosMeses(competencias, base).map((periodo) => ({
    rotulo: formatarPeriodo(periodo.de, periodo.ate),
    periodo,
  }))

// Anos com os 12 meses (jan a dez) dentro da base
function anosCompletos(competencias: string[]) {
  const anos = [...new Set(competencias.map((mes) => mes.slice(0, 4)))]
  return anos.filter((ano) => competencias.includes(`${ano}-01`) && competencias.includes(`${ano}-12`))
}
