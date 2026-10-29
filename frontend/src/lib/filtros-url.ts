import { ehClasseConsumo, type ClasseConsumo } from '@/config/classes'
import type { OpcoesFiltros } from '@/hooks/use-opcoes-filtros'
import {
  basePadrao,
  baseValida,
  comparadoPadrao,
  comparadoValido,
  periodoDeTamanho,
  tamanhoDoPeriodo,
  type PadraoComparacao,
  type Periodo,
} from '@/lib/periodos'

// Filtro ausente = sem filtro (todos). Meses no formato yyyy-MM
export type Filtros = {
  // Período base e começo do comparado, que tem o mesmo tamanho do base.
  // Sem eles, vale o padrão da tela (ver PadraoComparacao)
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
    ...lerComparacao(params.get('base_de'), params.get('base_ate'), params.get('comparado_de'), opcoes),
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

// Base e comparado em vigor: os escolhidos ou os padrões da tela. Um comparado
// que não cabe com o base em vigor volta para o padrão
export function periodosComparados(
  competencias: string[],
  { base_de, base_ate, comparado_de }: Pick<Filtros, 'base_de' | 'base_ate' | 'comparado_de'>,
  padrao: PadraoComparacao,
): { base: Periodo; comparado: Periodo } | undefined {
  const base = base_de && base_ate ? { de: base_de, ate: base_ate } : basePadrao(competencias, padrao)
  if (!base) {
    return undefined
  }
  const comparado =
    comparado_de && comparadoValido(competencias, base, comparado_de)
      ? periodoDeTamanho(competencias, comparado_de, tamanhoDoPeriodo(competencias, base))
      : comparadoPadrao(competencias, base)
  return comparado ? { base, comparado } : undefined
}

// Base inválido sai da URL lida; o comparado só depende do base em vigor, que
// muda de tela para tela, e é conferido em periodosComparados()
function lerComparacao(baseDe: string | null, baseAte: string | null, comparadoDe: string | null, opcoes?: OpcoesFiltros) {
  const baseLida =
    baseDe && baseAte && MES.test(baseDe) && MES.test(baseAte) && baseDe <= baseAte
      ? { de: baseDe, ate: baseAte }
      : undefined
  const base = baseLida && (!opcoes || baseValida(opcoes.competencias, baseLida)) ? baseLida : undefined
  const comparado =
    comparadoDe && MES.test(comparadoDe) && (!opcoes || opcoes.competencias.includes(comparadoDe))
      ? comparadoDe
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
