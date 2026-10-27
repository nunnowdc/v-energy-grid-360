import { ehClasseConsumo, type ClasseConsumo } from '@/config/classes'
import type { DecomposicaoReceita, NivelDetalhe, VariacaoReceita } from '@/hooks/use-receita'
import { linhaDoMes } from '@/mocks/indicadores'
import { opcoesFiltrosExemplo } from '@/mocks/opcoes-filtros'

// DADOS DE EXEMPLO para GET /api/metrics/revenue-variance. Não vêm da base real:
// partem dos mesmos números inventados dos Indicadores, divididos por bairro e por
// UCs com e sem geração própria. Como na base, as UCs com geração própria passam
// a medir bem menos consumo e puxam o efeito volume para baixo

const { competencias, municipios, classes } = opcoesFiltrosExemplo

// Primeiro ano da base e últimos 12 meses (períodos fixos da Gold)
const MESES_P0 = competencias.slice(0, 12)
const MESES_P1 = competencias.slice(-12)

// Parte das UCs com geração própria na receita e no consumo, em cada período
const PARTE_GD = {
  p0: { receita: 0.075, kwh: 0.08 },
  p1: { receita: 0.055, kwh: 0.05 },
}

type Valores = { receita: number; kwh: number; ucs: number }

type Linha = {
  municipio: string
  bairro: string
  classe: ClasseConsumo
  possui_gd: boolean
  p0: Valores
  p1: Valores
}

// Número entre -1 e 1, sempre igual para o mesmo texto
function sorteio(texto: string) {
  const semente = [...texto].reduce((soma, letra) => (soma * 31 + letra.charCodeAt(0)) % 9973, 7)
  return ((semente % 201) - 100) / 100
}

function somarMeses(meses: string[], municipio: string, classe: ClasseConsumo): Valores {
  return meses.reduce(
    (total, mes) => {
      const linha = linhaDoMes(competencias.indexOf(mes), municipio, classe)
      return {
        receita: total.receita + linha.receita_faturada,
        kwh: total.kwh + linha.consumo_kwh,
        ucs: Math.max(total.ucs, linha.ucs_faturadas),
      }
    },
    { receita: 0, kwh: 0, ucs: 0 },
  )
}

// Peso de cada bairro no município, em cada período. Cada bairro tem a própria
// tendência, mas os pesos somam 1 para o total bater com os Indicadores
function pesosBairros(bairros: string[]) {
  const base = bairros.map((bairro) => 1 + 0.4 * sorteio(bairro))
  const depois = base.map((peso, indice) => peso * (1 + 0.06 * sorteio(`${bairros[indice]}-p1`)))
  const normalizar = (pesos: number[]) => pesos.map((peso) => peso / pesos.reduce((a, b) => a + b, 0))
  return { p0: normalizar(base), p1: normalizar(depois) }
}

function partes(valores: Valores, peso: number, gd: boolean, parte: { receita: number; kwh: number }): Valores {
  const fatia = (fracao: number) => (gd ? fracao : 1 - fracao)
  return {
    receita: valores.receita * peso * fatia(parte.receita),
    kwh: valores.kwh * peso * fatia(parte.kwh),
    ucs: Math.round(valores.ucs * peso * fatia(0.07)),
  }
}

const linhas: Linha[] = municipios.flatMap(({ nome: municipio, bairros }) => {
  const pesos = pesosBairros(bairros)
  return classes.flatMap((classe) => {
    const p0 = somarMeses(MESES_P0, municipio, classe)
    const p1 = somarMeses(MESES_P1, municipio, classe)
    return bairros.flatMap((bairro, indice) =>
      [false, true].map((possui_gd) => ({
        municipio,
        bairro,
        classe,
        possui_gd,
        p0: partes(p0, pesos.p0[indice], possui_gd, PARTE_GD.p0),
        p1: partes(p1, pesos.p1[indice], possui_gd, PARTE_GD.p1),
      })),
    )
  })
})

const preco = (valores: Valores) => (valores.kwh > 0 ? valores.receita / valores.kwh : null)

// Soma as linhas como o backend faria: valores e efeitos somados linha a linha
function decompor(grupo: Linha[]): DecomposicaoReceita {
  const total: DecomposicaoReceita = {
    receita_p0: 0,
    receita_p1: 0,
    kwh_p0: 0,
    kwh_p1: 0,
    ucs_p0: 0,
    ucs_p1: 0,
    preco_p0: null,
    preco_p1: null,
    efeito_volume: 0,
    efeito_preco: 0,
  }
  for (const { p0, p1 } of grupo) {
    const precoP0 = preco(p0) ?? 0
    const precoP1 = preco(p1) ?? 0
    total.receita_p0 += p0.receita
    total.receita_p1 += p1.receita
    total.kwh_p0 += p0.kwh
    total.kwh_p1 += p1.kwh
    total.ucs_p0 += p0.ucs
    total.ucs_p1 += p1.ucs
    total.efeito_volume += (p1.kwh - p0.kwh) * precoP0
    total.efeito_preco += (precoP1 - precoP0) * p1.kwh
  }
  total.preco_p0 = preco({ receita: total.receita_p0, kwh: total.kwh_p0, ucs: 0 })
  total.preco_p1 = preco({ receita: total.receita_p1, kwh: total.kwh_p1, ucs: 0 })
  return total
}

function agrupar(grupo: Linha[], chave: (linha: Linha) => string) {
  const grupos = new Map<string, Linha[]>()
  for (const linha of grupo) {
    grupos.set(chave(linha), [...(grupos.get(chave(linha)) ?? []), linha])
  }
  return [...grupos].map(([nome, itens]) => ({ nome, ...decompor(itens) }))
}

export function gerarReceita(
  municipio?: string | null,
  bairro?: string | null,
  classe?: string | null,
): VariacaoReceita {
  const recorte = linhas.filter(
    (linha) =>
      (!municipio || linha.municipio === municipio) &&
      (!bairro || linha.bairro === bairro) &&
      (!ehClasseConsumo(classe) || linha.classe === classe),
  )
  const nivel: NivelDetalhe = !municipio ? 'municipio' : !bairro ? 'bairro' : 'classe'

  return {
    periodo_p0: { inicio: MESES_P0[0], fim: MESES_P0.at(-1)! },
    periodo_p1: { inicio: MESES_P1[0], fim: MESES_P1.at(-1)! },
    total: decompor(recorte),
    por_gd: [false, true].map((possui_gd) => ({
      possui_gd,
      ...decompor(recorte.filter((linha) => linha.possui_gd === possui_gd)),
    })),
    detalhamento: { nivel, linhas: agrupar(recorte, (linha) => linha[nivel]) },
  }
}
