import { ehClasseConsumo, type ClasseConsumo } from '@/config/classes'
import type { OpcoesFiltros } from '@/hooks/use-opcoes-filtros'
import {
  basePadrao,
  baseValida,
  comparadoPadrao,
  comparadoValido,
  periodoComAnterior,
  periodoDeTamanho,
  periodoPadrao,
  tamanhoDoPeriodo,
  type Periodo,
} from '@/lib/periodos'

// Filtro ausente = sem filtro (todos). Meses no formato yyyy-MM
export type Filtros = {
  // Período dos Indicadores e da Continuidade. Sem ele, os últimos 12 meses da base
  de?: string
  ate?: string
  // Receita: período base e começo do comparado, que tem o mesmo tamanho do base.
  // Sem eles, o primeiro ano da base contra os mesmos meses do último ano
  base_de?: string
  base_ate?: string
  comparado_de?: string
  municipio?: string
  bairro?: string
  classe?: ClasseConsumo
  alimentador?: string
  causa?: string
}

export type NomeFiltro = keyof Filtros

export const nomesFiltros: NomeFiltro[] = [
  'de',
  'ate',
  'base_de',
  'base_ate',
  'comparado_de',
  'municipio',
  'bairro',
  'classe',
  'alimentador',
  'causa',
]

const MES = /^\d{4}-(0[1-9]|1[0-2])$/

// Lê os filtros da URL, descartando valores que não existem.
// Enquanto as opções não chegam, aceita os textos como vieram
export function lerFiltros(params: URLSearchParams, opcoes?: OpcoesFiltros): Filtros {
  const municipio = lerMunicipio(params.get('municipio'), opcoes)
  const bairro = municipio ? lerBairro(params.get('bairro'), municipio, opcoes) : undefined
  const classe = params.get('classe')

  return {
    ...lerPeriodo(params.get('de'), params.get('ate'), opcoes),
    ...lerReceita(params.get('base_de'), params.get('base_ate'), params.get('comparado_de'), opcoes),
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

// Vários filtros de uma vez, ex.: o começo e o fim de um período
export function aplicarFiltros(
  params: URLSearchParams,
  valores: Partial<Record<NomeFiltro, string | undefined>>,
  opcoes?: OpcoesFiltros,
) {
  return (Object.entries(valores) as [NomeFiltro, string | undefined][]).reduce(
    (atual, [nome, valor]) => aplicarFiltro(atual, nome, valor, opcoes),
    params,
  )
}

// Remove só os filtros, mantendo outros parâmetros da URL
export function removerFiltros(params: URLSearchParams) {
  const proximo = new URLSearchParams(params)
  for (const nome of nomesFiltros) {
    proximo.delete(nome)
  }
  return proximo
}

// Período em vigor nos Indicadores e na Continuidade: o escolhido ou o padrão
export function periodoEscolhido(competencias: string[], { de, ate }: Pick<Filtros, 'de' | 'ate'>) {
  return de && ate ? { de, ate } : periodoPadrao(competencias)
}

// Base e comparado em vigor na Receita: os escolhidos ou os padrões
export function periodosDaReceita(
  competencias: string[],
  { base_de, base_ate, comparado_de }: Pick<Filtros, 'base_de' | 'base_ate' | 'comparado_de'>,
): { base: Periodo; comparado: Periodo } | undefined {
  const base = base_de && base_ate ? { de: base_de, ate: base_ate } : basePadrao(competencias)
  if (!base) {
    return undefined
  }
  const comparado = comparado_de
    ? periodoDeTamanho(competencias, comparado_de, tamanhoDoPeriodo(competencias, base))
    : comparadoPadrao(competencias, base)
  return comparado ? { base, comparado } : undefined
}

// Os dois meses ou nenhum. Com as opções, o período anterior tem que caber na base
function lerPeriodo(de: string | null, ate: string | null, opcoes?: OpcoesFiltros) {
  const nenhum = { de: undefined, ate: undefined }
  if (!de || !ate || !MES.test(de) || !MES.test(ate) || de > ate) {
    return nenhum
  }
  if (opcoes && !periodoComAnterior(opcoes.competencias, { de, ate })) {
    return nenhum
  }
  return { de, ate }
}

// Base inválido volta tudo para o padrão; comparado inválido volta só ele
function lerReceita(baseDe: string | null, baseAte: string | null, comparadoDe: string | null, opcoes?: OpcoesFiltros) {
  const baseLida =
    baseDe && baseAte && MES.test(baseDe) && MES.test(baseAte) && baseDe <= baseAte
      ? { de: baseDe, ate: baseAte }
      : undefined
  const comparadoLido = comparadoDe && MES.test(comparadoDe) ? comparadoDe : undefined
  if (!opcoes) {
    return { base_de: baseLida?.de, base_ate: baseLida?.ate, comparado_de: comparadoLido }
  }

  const base = baseLida && baseValida(opcoes.competencias, baseLida) ? baseLida : undefined
  const baseEmVigor = base ?? basePadrao(opcoes.competencias)
  const comparado =
    comparadoLido && baseEmVigor && comparadoValido(opcoes.competencias, baseEmVigor, comparadoLido)
      ? comparadoLido
      : undefined
  return { base_de: base?.de, base_ate: base?.ate, comparado_de: comparado }
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
