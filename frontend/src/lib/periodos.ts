import { formatarPeriodo } from '@/lib/formatacao'

// Períodos escolhidos nos filtros: intervalos de meses (yyyy-MM) dentro da base.
// Indicadores e Continuidade comparam com o período anterior, de mesmo tamanho;
// a Receita compara um período base com um período comparado, também de mesmo tamanho

export type Periodo = { de: string; ate: string }

export type AtalhoPeriodo = { rotulo: string; periodo: Periodo }

// Com a comparação do outro lado, até 24 meses cabem nos 48 meses da base
export const MAXIMO_MESES = 24
const MESES_PADRAO = 12

const posicoes = (competencias: string[], { de, ate }: Periodo) => {
  const inicio = competencias.indexOf(de)
  const fim = competencias.indexOf(ate)
  return { inicio, fim, tamanho: fim - inicio + 1 }
}

export const tamanhoDoPeriodo = (competencias: string[], periodo: Periodo) => posicoes(competencias, periodo).tamanho

const dentroDoLimite = (inicio: number, fim: number) => inicio >= 0 && fim >= inicio && fim - inicio + 1 <= MAXIMO_MESES

// N meses a partir de "de"; undefined se passar do fim da base
export function periodoDeTamanho(competencias: string[], de: string, tamanho: number): Periodo | undefined {
  const inicio = competencias.indexOf(de)
  const ate = competencias[inicio + tamanho - 1]
  return inicio >= 0 && ate ? { de, ate } : undefined
}

// Mesmos meses do ano dos dois lados (jan–mar × jan–mar): sem efeito da estação
export const mesmosMesesDoAno = (a: Periodo, b: Periodo) => a.de.slice(5) === b.de.slice(5)

// ---------- Indicadores e Continuidade ----------

// Antes do período precisa caber o anterior, de mesmo tamanho
export function periodoComAnterior(competencias: string[], periodo: Periodo) {
  const { inicio, fim, tamanho } = posicoes(competencias, periodo)
  return dentroDoLimite(inicio, fim) && inicio >= tamanho
}

// Os últimos 12 meses da base, nunca contados da data de hoje
export function periodoPadrao(competencias: string[]): Periodo | undefined {
  const ultimos = competencias.slice(-MESES_PADRAO)
  return ultimos.length === MESES_PADRAO ? { de: ultimos[0], ate: ultimos[MESES_PADRAO - 1] } : undefined
}

export function atalhosDoPeriodo(competencias: string[]): AtalhoPeriodo[] {
  const ultimos = [3, 6, 12, 24].map((meses) => ({
    rotulo: `Últimos ${meses} meses`,
    periodo: { de: competencias.at(-meses) ?? '', ate: competencias.at(-1) ?? '' },
  }))
  const anosCivis = anosCompletos(competencias).map((ano) => ({
    rotulo: `Ano de ${ano}`,
    periodo: { de: `${ano}-01`, ate: `${ano}-12` },
  }))
  return [...ultimos, ...anosCivis].filter(({ periodo }) => periodoComAnterior(competencias, periodo))
}

// ---------- Receita ----------

// Depois do base precisa caber o comparado, de mesmo tamanho
export function baseValida(competencias: string[], base: Periodo) {
  const { inicio, fim, tamanho } = posicoes(competencias, base)
  return dentroDoLimite(inicio, fim) && fim + tamanho <= competencias.length - 1
}

// O comparado começa depois do fim do base e cabe na base
export function comparadoValido(competencias: string[], base: Periodo, de: string) {
  const { fim, tamanho } = posicoes(competencias, base)
  const inicio = competencias.indexOf(de)
  return inicio > fim && inicio + tamanho - 1 <= competencias.length - 1
}

// O primeiro ano da base, a pergunta do case
export function basePadrao(competencias: string[]): Periodo | undefined {
  const base = periodoDeTamanho(competencias, competencias[0] ?? '', MESES_PADRAO)
  return base && baseValida(competencias, base) ? base : undefined
}

// Os comparados com os mesmos meses do ano do base, do mais antigo ao mais recente
export function comparadosComMesmosMeses(competencias: string[], base: Periodo): Periodo[] {
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

// ---------- auxiliares ----------

// Anos com os 12 meses (jan a dez) dentro da base
function anosCompletos(competencias: string[]) {
  const anos = [...new Set(competencias.map((mes) => mes.slice(0, 4)))]
  return anos.filter((ano) => competencias.includes(`${ano}-01`) && competencias.includes(`${ano}-12`))
}
