import type { AlimentadorContinuidade, ContinuidadeRede, MesContinuidade } from '@/hooks/use-continuidade'
import type { OpcoesFiltros } from '@/hooks/use-opcoes-filtros'
import { mesesPeriodo } from '@/lib/filtros-url'

// DADOS DE EXEMPLO para GET /api/network/continuity. Os números não vêm da base
// real: são inventados por alimentador, com mais interrupções na época de chuva
// (abril a julho) e uma tempestade em jul/2025, como a da base (dias críticos).
// Os alimentadores e as causas são os das opções dos filtros (src/mocks/opcoes-atuais.ts)

const MES_TEMPESTADE = '2025-07'

// Peso de cada causa nas ocorrências de um alimentador típico
const pesoCausa: Record<string, number> = {
  VEGETACAO: 0.28,
  'FALHA DE EQUIPAMENTO': 0.2,
  CLIMATICA: 0.15,
  TERCEIROS: 0.12,
  SOBRECARGA: 0.1,
  'NAO IDENTIFICADA': 0.08,
  'NAO INFORMADA': 0.07,
}

// Número entre 0 e 1, sempre igual para o mesmo texto
function sorteio(texto: string) {
  const semente = [...texto].reduce((soma, letra) => (soma * 31 + letra.charCodeAt(0)) % 99_991, 7)
  return (semente % 1000) / 1000
}

type MesAlimentador = MesContinuidade & { dec_sem_dia_critico: number; ocorrencias: Record<string, number> }

function mesDoAlimentador(opcoes: OpcoesFiltros, codigo: string, indice: number, totalUcs: number): MesAlimentador {
  const mesReferencia = opcoes.competencias[indice]
  const mes = Number(mesReferencia.slice(5))
  const anos = indice / 12
  const chuva = mes >= 4 && mes <= 7 ? 1.35 : 1
  // Cada alimentador tem o seu nível de problema e a sua tendência
  const nivel = 0.15 + 0.85 * sorteio(codigo)
  const tendencia = 1 + (sorteio(`${codigo}-tendencia`) - 0.5) * 0.3 * anos
  const variacaoDoMes = 0.85 + 0.3 * sorteio(`${codigo}-${mesReferencia}`)
  const tempestade = mesReferencia === MES_TEMPESTADE

  const decNormal = nivel * tendencia * chuva * variacaoDoMes
  const dec = tempestade ? decNormal * 3 : decNormal
  const fec = (tempestade ? 2 : 1) * (0.2 + 0.4 * sorteio(`${codigo}-fec`)) * chuva * variacaoDoMes
  const total = fec * totalUcs

  const ocorrencias = Object.fromEntries(
    opcoes.causas.map((causa) => {
      const extra = tempestade && causa === 'CLIMATICA' ? 3 : 1
      const peso = (pesoCausa[causa] ?? 0.05) * (0.6 + 0.8 * sorteio(`${codigo}-${causa}`)) * extra
      return [causa, total * peso]
    }),
  )

  return { mes_referencia: mesReferencia, dec, fec, dec_sem_dia_critico: decNormal, ocorrencias }
}

const somarDec = (meses: MesAlimentador[], campo: 'dec' | 'fec' | 'dec_sem_dia_critico') =>
  meses.reduce((soma, mes) => soma + mes[campo], 0)

// Devolve undefined quando o período não é um dos aceitos (o backend responde 422)
export function gerarContinuidade(
  opcoes: OpcoesFiltros,
  inicio: string | null,
  fim: string | null,
  municipio?: string | null,
  alimentador?: string | null,
  causa?: string | null,
): ContinuidadeRede | undefined {
  const { competencias } = opcoes
  const primeiro = competencias.indexOf(inicio ?? '')
  const ultimo = competencias.indexOf(fim ?? '')
  const tamanho = ultimo - primeiro + 1
  if (primeiro < 0 || ultimo < 0 || !mesesPeriodo.some((meses) => meses === tamanho) || primeiro < tamanho) {
    return undefined
  }

  const indicesAtual = Array.from({ length: tamanho }, (_, posicao) => primeiro + posicao)
  const indicesAnterior = indicesAtual.map((indice) => indice - tamanho)

  // Município só escolhe os alimentadores que entram; DEC e FEC são do alimentador inteiro
  const recorte = opcoes.alimentadores.filter(
    (item) => (!alimentador || item.codigo === alimentador) && (!municipio || item.municipios.includes(municipio)),
  )

  const alimentadores = recorte.map(({ codigo, municipios }) => {
    const totalUcs = 40 + Math.round(900 * sorteio(`${codigo}-ucs`))
    const atual = indicesAtual.map((indice) => mesDoAlimentador(opcoes, codigo, indice, totalUcs))
    const anterior = indicesAnterior.map((indice) => mesDoAlimentador(opcoes, codigo, indice, totalUcs))
    const linha: AlimentadorContinuidade = {
      alimentador: codigo,
      municipio_principal: municipios[0] ?? '',
      total_ucs: totalUcs,
      alimentador_pequeno: totalUcs < 100,
      dec: somarDec(atual, 'dec'),
      fec: somarDec(atual, 'fec'),
      dec_sem_dia_critico: somarDec(atual, 'dec_sem_dia_critico'),
      dec_anterior: somarDec(anterior, 'dec'),
    }
    return { linha, atual, anterior }
  })

  const ranking = alimentadores.map(({ linha }) => linha).sort((a, b) => b.dec - a.dec)
  const destaque = alimentadores.find(({ linha }) => linha.alimentador === ranking[0]?.alimentador)
  const paraMes = ({ mes_referencia, dec, fec }: MesAlimentador): MesContinuidade => ({ mes_referencia, dec, fec })

  // A causa filtra só as ocorrências
  const causas = opcoes.causas.filter((item) => !causa || item === causa)
  const contar = (periodo: 'atual' | 'anterior', item: string) =>
    Math.round(
      alimentadores.reduce(
        (soma, dados) => soma + dados[periodo].reduce((somaMes, mes) => somaMes + (mes.ocorrencias[item] ?? 0), 0),
        0,
      ),
    )
  const porCausa = causas
    .map((item) => ({ causa: item, ocorrencias: contar('atual', item) }))
    .sort((a, b) => b.ocorrencias - a.ocorrencias)

  return {
    periodo: { inicio: competencias[primeiro], fim: competencias[ultimo] },
    periodo_anterior: { inicio: competencias[primeiro - tamanho], fim: competencias[primeiro - 1] },
    ranking,
    serie: destaque
      ? {
          alimentador: destaque.linha.alimentador,
          atual: destaque.atual.map(paraMes),
          anterior: destaque.anterior.map(paraMes),
        }
      : null,
    ocorrencias: {
      total: porCausa.reduce((soma, item) => soma + item.ocorrencias, 0),
      total_anterior: causas.reduce((soma, item) => soma + contar('anterior', item), 0),
      por_causa: porCausa,
    },
  }
}
