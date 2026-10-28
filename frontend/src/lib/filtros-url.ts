import { ehClasseConsumo, type ClasseConsumo } from '@/config/classes'
import type { OpcoesFiltros } from '@/hooks/use-opcoes-filtros'

// Períodos aceitos pelo backend: os últimos 3, 6 ou 12 meses da base
export const mesesPeriodo = [12, 6, 3] as const
export type MesesPeriodo = (typeof mesesPeriodo)[number]
export const MESES_PADRAO: MesesPeriodo = 12

// Filtro ausente = sem filtro (todos). Sem período = últimos 12 meses da base
export type Filtros = {
  meses?: MesesPeriodo
  municipio?: string
  bairro?: string
  classe?: ClasseConsumo
  alimentador?: string
  causa?: string
}

export type NomeFiltro = keyof Filtros

export const nomesFiltros: NomeFiltro[] = ['meses', 'municipio', 'bairro', 'classe', 'alimentador', 'causa']

// Lê os filtros da URL, descartando valores que não existem.
// Enquanto as opções não chegam, aceita os textos como vieram
export function lerFiltros(params: URLSearchParams, opcoes?: OpcoesFiltros): Filtros {
  const municipio = lerMunicipio(params.get('municipio'), opcoes)
  const bairro = municipio ? lerBairro(params.get('bairro'), municipio, opcoes) : undefined
  const classe = params.get('classe')

  return {
    meses: lerMeses(params.get('meses')),
    municipio,
    bairro,
    classe: ehClasseConsumo(classe) ? classe : undefined,
    alimentador: lerAlimentador(params.get('alimentador'), municipio, opcoes),
    causa: lerCausa(params.get('causa'), opcoes),
  }
}

// Devolve a URL com um filtro trocado (valor vazio remove o filtro)
export function aplicarFiltro(
  params: URLSearchParams,
  nome: NomeFiltro,
  valor?: string,
  opcoes?: OpcoesFiltros,
) {
  const proximo = new URLSearchParams(params)

  if (valor) {
    proximo.set(nome, valor)
  } else {
    proximo.delete(nome)
  }

  if (nome === 'municipio') {
    // O bairro pertence ao município: trocar o município zera o bairro
    proximo.delete('bairro')
    // O alimentador só sai se não atender o município novo
    const alimentador = proximo.get('alimentador')
    if (valor && alimentador && !atendeMunicipio(alimentador, valor, opcoes)) {
      proximo.delete('alimentador')
    }
  }

  return proximo
}

// Remove só os filtros, mantendo outros parâmetros da URL
export function removerFiltros(params: URLSearchParams) {
  const proximo = new URLSearchParams(params)
  for (const nome of nomesFiltros) {
    proximo.delete(nome)
  }
  return proximo
}

// Primeiro e último mês (yyyy-MM) dos últimos N meses da base.
// A âncora é o último mês da base, nunca a data de hoje
export function janelaDoPeriodo(competencias: string[], meses: MesesPeriodo = MESES_PADRAO) {
  const janela = competencias.slice(-meses)
  return { inicio: janela[0], fim: janela.at(-1) }
}

function lerMeses(valor: string | null) {
  return mesesPeriodo.find((meses) => String(meses) === valor)
}

function lerMunicipio(valor: string | null, opcoes?: OpcoesFiltros) {
  if (!valor) {
    return undefined
  }
  if (opcoes && !opcoes.municipios.some((municipio) => municipio.nome === valor)) {
    return undefined
  }
  return valor
}

function lerBairro(valor: string | null, municipio: string, opcoes?: OpcoesFiltros) {
  if (!valor) {
    return undefined
  }
  const bairros = opcoes?.municipios.find((item) => item.nome === municipio)?.bairros
  if (bairros && !bairros.includes(valor)) {
    return undefined
  }
  return valor
}

function lerAlimentador(valor: string | null, municipio: string | undefined, opcoes?: OpcoesFiltros) {
  if (!valor || !opcoes) {
    return valor ?? undefined
  }
  const alimentador = opcoes.alimentadores.find((item) => item.codigo === valor)
  if (!alimentador || (municipio && !alimentador.municipios.includes(municipio))) {
    return undefined
  }
  return valor
}

function lerCausa(valor: string | null, opcoes?: OpcoesFiltros) {
  if (!valor || (opcoes && !opcoes.causas.includes(valor))) {
    return undefined
  }
  return valor
}

// Sem as opções carregadas, não dá para saber: mantém a escolha
function atendeMunicipio(codigo: string, municipio: string, opcoes?: OpcoesFiltros) {
  const alimentador = opcoes?.alimentadores.find((item) => item.codigo === codigo)
  return !opcoes || Boolean(alimentador?.municipios.includes(municipio))
}
