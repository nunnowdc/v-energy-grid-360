import { ehClasseConsumo, type ClasseConsumo } from '@/config/classes'
import type { IndicadoresGerais, MesIndicadores, ResumoIndicadores } from '@/hooks/use-indicadores'
import type { OpcoesFiltros } from '@/hooks/use-opcoes-filtros'
import { mesesPeriodo } from '@/lib/filtros-url'

// DADOS DE EXEMPLO para GET /api/metrics/general. Os números não vêm da base real:
// são inventados, com verão mais caro, receita subindo e consumo caindo.
// Os municípios e classes são os das opções dos filtros (src/mocks/opcoes-atuais.ts)

// Parte de cada município no total (soma 1): quanto mais bairros, maior
const pesosPorOpcoes = new WeakMap<OpcoesFiltros, Map<string, number>>()

function pesoMunicipio(opcoes: OpcoesFiltros, municipio: string) {
  let pesos = pesosPorOpcoes.get(opcoes)
  if (!pesos) {
    const total = opcoes.municipios.reduce((soma, { bairros }) => soma + bairros.length + 3, 0)
    pesos = new Map(opcoes.municipios.map(({ nome, bairros }) => [nome, (bairros.length + 3) / total]))
    pesosPorOpcoes.set(opcoes, pesos)
  }
  return pesos.get(municipio) ?? 0
}

// Parte de cada classe na receita, no consumo e nas UCs, e quanto receita e
// consumo mudam por ano (cada classe com a sua tendência)
type PerfilClasse = { receita: number; consumo: number; ucs: number; ritmoReceita: number; ritmoConsumo: number }

const perfilClasse: Record<ClasseConsumo, PerfilClasse> = {
  RESIDENCIAL: { receita: 0.5, consumo: 0.47, ucs: 0.87, ritmoReceita: 0.034, ritmoConsumo: -0.012 },
  COMERCIAL: { receita: 0.25, consumo: 0.24, ucs: 0.08, ritmoReceita: 0.052, ritmoConsumo: 0.004 },
  INDUSTRIAL: { receita: 0.13, consumo: 0.17, ucs: 0.01, ritmoReceita: -0.021, ritmoConsumo: -0.048 },
  RURAL: { receita: 0.04, consumo: 0.05, ucs: 0.02, ritmoReceita: 0.078, ritmoConsumo: 0.031 },
  PODER_PUBLICO: { receita: 0.08, consumo: 0.07, ucs: 0.02, ritmoReceita: 0.012, ritmoConsumo: -0.026 },
}

type LinhaMes = MesIndicadores & { ucs_faturadas: number; faturas: number; faturas_atrasadas: number }

// Variação pequena e sempre igual para a mesma combinação (±2%)
function ruido(...chaves: number[]) {
  const semente = chaves.reduce((soma, chave) => (soma * 31 + chave) % 9973, 7)
  return 1 + ((semente % 41) - 20) / 1000
}

// Um mês de um município e classe
function linhaDoMes(opcoes: OpcoesFiltros, indice: number, municipio: string, classe: ClasseConsumo): LinhaMes {
  const { competencias } = opcoes
  const mes = Number(competencias[indice].slice(5))
  const anos = indice / 12
  // Mais calor (e mais consumo) de dezembro a março
  const sazonal = 1 + 0.08 * Math.cos(((mes - 1.5) / 12) * 2 * Math.PI)
  const peso = pesoMunicipio(opcoes, municipio) * ruido(indice, municipio.length, classe.length)
  const perfil = perfilClasse[classe]
  const ucs = Math.round(41_800 * (1 + 0.006 * anos) * pesoMunicipio(opcoes, municipio) * perfil.ucs)
  // As faturas dos últimos meses ainda estão vencendo
  const taxaAtraso = indice >= competencias.length - 2 ? 0.045 : 0.03

  return {
    mes_referencia: competencias[indice],
    receita_faturada: 14_100_000 * (1 + perfil.ritmoReceita * anos) * sazonal * peso * perfil.receita,
    consumo_kwh: 19_400_000 * (1 + perfil.ritmoConsumo * anos) * sazonal * peso * perfil.consumo,
    ucs_faturadas: ucs,
    faturas: ucs,
    faturas_atrasadas: Math.round(ucs * taxaAtraso),
  }
}

function somar(linhas: LinhaMes[], mes_referencia: string): LinhaMes {
  const zero = { mes_referencia, receita_faturada: 0, consumo_kwh: 0, ucs_faturadas: 0, faturas: 0, faturas_atrasadas: 0 }
  return linhas.reduce(
    (total, linha) => ({
      mes_referencia,
      receita_faturada: total.receita_faturada + linha.receita_faturada,
      consumo_kwh: total.consumo_kwh + linha.consumo_kwh,
      ucs_faturadas: total.ucs_faturadas + linha.ucs_faturadas,
      faturas: total.faturas + linha.faturas,
      faturas_atrasadas: total.faturas_atrasadas + linha.faturas_atrasadas,
    }),
    zero,
  )
}

function resumir(meses: LinhaMes[]): ResumoIndicadores {
  const total = somar(meses, '')
  return {
    inicio: meses[0].mes_referencia,
    fim: meses.at(-1)!.mes_referencia,
    receita_faturada: total.receita_faturada,
    consumo_kwh: total.consumo_kwh,
    preco_medio_kwh: total.consumo_kwh > 0 ? total.receita_faturada / total.consumo_kwh : null,
    ucs_faturadas: meses.at(-1)!.ucs_faturadas,
    faturas: total.faturas,
    faturas_atrasadas: total.faturas_atrasadas,
  }
}

const paraMes = ({ mes_referencia, receita_faturada, consumo_kwh }: LinhaMes): MesIndicadores => ({
  mes_referencia,
  receita_faturada,
  consumo_kwh,
})

// Devolve undefined quando o período não é um dos aceitos (o backend responde 422)
export function gerarIndicadores(
  opcoes: OpcoesFiltros,
  inicio: string | null,
  fim: string | null,
  municipio?: string | null,
  classe?: string | null,
): IndicadoresGerais | undefined {
  const { competencias, municipios, classes } = opcoes
  const primeiro = competencias.indexOf(inicio ?? '')
  const ultimo = competencias.indexOf(fim ?? '')
  const tamanho = ultimo - primeiro + 1
  if (primeiro < 0 || ultimo < 0 || !mesesPeriodo.some((meses) => meses === tamanho) || primeiro < tamanho) {
    return undefined
  }

  const nomesMunicipios = municipios.map(({ nome }) => nome).filter((nome) => !municipio || nome === municipio)
  const classesEscolhidas = classes.filter((item) => !ehClasseConsumo(classe) || item === classe)

  const mesDoRecorte = (indice: number, classesDoMes = classesEscolhidas) =>
    somar(
      nomesMunicipios.flatMap((nome) => classesDoMes.map((item) => linhaDoMes(opcoes, indice, nome, item))),
      competencias[indice],
    )
  const indicesAtual = Array.from({ length: tamanho }, (_, posicao) => primeiro + posicao)
  const indicesAnterior = indicesAtual.map((indice) => indice - tamanho)
  const atual = indicesAtual.map((indice) => mesDoRecorte(indice))
  const anterior = indicesAnterior.map((indice) => mesDoRecorte(indice))

  const receitaDaClasse = (indices: number[], item: ClasseConsumo) =>
    indices.reduce((soma, indice) => soma + mesDoRecorte(indice, [item]).receita_faturada, 0)

  return {
    atual: resumir(atual),
    anterior: resumir(anterior),
    mensal: { atual: atual.map(paraMes), anterior: anterior.map(paraMes) },
    por_classe: classesEscolhidas.map((item) => ({
      classe: item,
      receita_faturada: receitaDaClasse(indicesAtual, item),
      receita_faturada_anterior: receitaDaClasse(indicesAnterior, item),
    })),
  }
}
