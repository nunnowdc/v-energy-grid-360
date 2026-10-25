import { ehClasseConsumo, type ClasseConsumo } from '@/config/classes'
import type { OpcoesFiltros } from '@/hooks/use-opcoes-filtros'

// Filtro ausente = sem filtro (todos). Sem período = últimos 12 meses da base
export type Filtros = {
  inicio?: string
  fim?: string
  municipio?: string
  bairro?: string
  classe?: ClasseConsumo
}

export type NomeFiltro = keyof Filtros

export const nomesFiltros: NomeFiltro[] = ['inicio', 'fim', 'municipio', 'bairro', 'classe']

const FORMATO_COMPETENCIA = /^\d{4}-(0[1-9]|1[0-2])$/

// Lê os filtros da URL, descartando valores que não existem.
// Enquanto as opções não chegam, confere só o formato
export function lerFiltros(params: URLSearchParams, opcoes?: OpcoesFiltros): Filtros {
  const inicioUrl = lerCompetencia(params.get('inicio'), opcoes)
  const fimUrl = lerCompetencia(params.get('fim'), opcoes)
  // Período invertido digitado na URL: troca os dois de lugar
  const invertido = inicioUrl && fimUrl && inicioUrl > fimUrl
  const inicio = invertido ? fimUrl : inicioUrl
  const fim = invertido ? inicioUrl : fimUrl

  const municipio = lerMunicipio(params.get('municipio'), opcoes)
  const bairro = municipio ? lerBairro(params.get('bairro'), municipio, opcoes) : undefined
  const classe = params.get('classe')

  return {
    inicio,
    fim,
    municipio,
    bairro,
    classe: ehClasseConsumo(classe) ? classe : undefined,
  }
}

// Devolve a URL com um filtro trocado (valor vazio remove o filtro)
export function aplicarFiltro(params: URLSearchParams, nome: NomeFiltro, valor?: string) {
  const proximo = new URLSearchParams(params)

  if (valor) {
    proximo.set(nome, valor)
  } else {
    proximo.delete(nome)
  }

  // O bairro pertence ao município: trocar o município zera o bairro
  if (nome === 'municipio') {
    proximo.delete('bairro')
  }

  // O início nunca fica depois do fim: o outro lado acompanha a escolha
  const inicio = proximo.get('inicio')
  const fim = proximo.get('fim')
  if (inicio && fim && inicio > fim) {
    proximo.set(nome === 'inicio' ? 'fim' : 'inicio', nome === 'inicio' ? inicio : fim)
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

function lerCompetencia(valor: string | null, opcoes?: OpcoesFiltros) {
  if (!valor || !FORMATO_COMPETENCIA.test(valor)) {
    return undefined
  }
  if (opcoes && !opcoes.competencias.includes(valor)) {
    return undefined
  }
  return valor
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
