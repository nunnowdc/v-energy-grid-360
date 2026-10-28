import { ehClasseConsumo, type ClasseConsumo } from '@/config/classes'
import type { OpcoesFiltros } from '@/hooks/use-opcoes-filtros'

// Tamanhos de período aceitos pelo backend nos Indicadores: 3, 6 ou 12 meses
export const mesesPeriodo = [12, 6, 3] as const
export type MesesPeriodo = (typeof mesesPeriodo)[number]
export const MESES_PADRAO: MesesPeriodo = 12

// Filtro ausente = sem filtro (todos). Sem período = últimos 12 meses da base
export type Filtros = {
  meses?: MesesPeriodo
  // Último mês (yyyy-MM) do período dos Indicadores. Sem ele, o último mês da base
  ate?: string
  // Primeiro mês (yyyy-MM) do ano base e do ano comparado da Receita. Sem eles,
  // o primeiro ano da base contra os últimos 12 meses
  base?: string
  comparado?: string
  municipio?: string
  bairro?: string
  classe?: ClasseConsumo
  alimentador?: string
  causa?: string
}

export type NomeFiltro = keyof Filtros

export const nomesFiltros: NomeFiltro[] = [
  'meses',
  'ate',
  'base',
  'comparado',
  'municipio',
  'bairro',
  'classe',
  'alimentador',
  'causa',
]

// Um ano da Receita: 12 meses seguidos (yyyy-MM)
export type AnoDaBase = { inicio: string; fim: string }

const MES = /^\d{4}-(0[1-9]|1[0-2])$/

// Lê os filtros da URL, descartando valores que não existem.
// Enquanto as opções não chegam, aceita os textos como vieram
export function lerFiltros(params: URLSearchParams, opcoes?: OpcoesFiltros): Filtros {
  const municipio = lerMunicipio(params.get('municipio'), opcoes)
  const bairro = municipio ? lerBairro(params.get('bairro'), municipio, opcoes) : undefined
  const classe = params.get('classe')
  const meses = lerMeses(params.get('meses'))

  return {
    meses,
    ate: lerAte(params.get('ate'), meses, opcoes),
    ...lerAnos(params.get('base'), params.get('comparado'), opcoes),
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

  // O fim escolhido sai se, com o novo tamanho, não couber o período anterior
  const ate = proximo.get('ate')
  if (nome === 'meses' && ate && opcoes && !mesesFinais(opcoes.competencias, lerMeses(valor ?? null)).includes(ate)) {
    proximo.delete('ate')
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

// Primeiro e último mês (yyyy-MM) dos N meses que terminam em "ate".
// Sem "ate", a âncora é o último mês da base, nunca a data de hoje
export function janelaDoPeriodo(competencias: string[], meses: MesesPeriodo = MESES_PADRAO, ate?: string) {
  const fim = ate === undefined ? competencias.length : competencias.indexOf(ate) + 1
  const janela = fim < meses ? [] : competencias.slice(fim - meses, fim)
  return { inicio: janela[0], fim: janela.at(-1) }
}

// Meses em que o período pode terminar: antes dele precisa caber o período
// anterior, de mesmo tamanho, que é a comparação dos Indicadores
export function mesesFinais(competencias: string[], meses: MesesPeriodo = MESES_PADRAO) {
  return competencias.slice(2 * meses - 1)
}

// Anos da Receita, contados do fim da base para trás (… jul/2024–jun/2025,
// jul/2025–jun/2026): os dois lados da comparação têm sempre os mesmos meses do ano
export function anosDaBase(competencias: string[]): AnoDaBase[] {
  const anos: AnoDaBase[] = []
  for (let fim = competencias.length; fim >= 12; fim -= 12) {
    anos.unshift({ inicio: competencias[fim - 12], fim: competencias[fim - 1] })
  }
  return anos
}

// Ano base e ano comparado em vigor: sem escolha, o primeiro e o último ano
export function anosDaReceita(competencias: string[], { base, comparado }: Pick<Filtros, 'base' | 'comparado'>) {
  const anos = anosDaBase(competencias)
  return { base: base ?? anos[0]?.inicio, comparado: comparado ?? anos.at(-1)?.inicio }
}

function lerMeses(valor: string | null) {
  return mesesPeriodo.find((meses) => String(meses) === valor)
}

function lerAte(valor: string | null, meses: MesesPeriodo | undefined, opcoes?: OpcoesFiltros) {
  if (!valor) {
    return undefined
  }
  if (opcoes) {
    return mesesFinais(opcoes.competencias, meses).includes(valor) ? valor : undefined
  }
  return MES.test(valor) ? valor : undefined
}

// Cada um tem que ser o começo de um ano da base, e o comparado vem depois do base.
// Uma combinação impossível volta para o padrão
function lerAnos(base: string | null, comparado: string | null, opcoes?: OpcoesFiltros) {
  if (!opcoes) {
    return {
      base: base && MES.test(base) ? base : undefined,
      comparado: comparado && MES.test(comparado) ? comparado : undefined,
    }
  }
  const inicios = anosDaBase(opcoes.competencias).map(({ inicio }) => inicio)
  const escolhidos = {
    base: base && inicios.includes(base) ? base : undefined,
    comparado: comparado && inicios.includes(comparado) ? comparado : undefined,
  }
  const emVigor = anosDaReceita(opcoes.competencias, escolhidos)
  if (!emVigor.base || !emVigor.comparado || emVigor.base >= emVigor.comparado) {
    return { base: undefined, comparado: undefined }
  }
  return escolhidos
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
