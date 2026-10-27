import { ehClasseConsumo, type ClasseConsumo } from '@/config/classes'
import type { FilaInspecao, ItemFila } from '@/hooks/use-fila-inspecao'
import type { MudancaOrdem, OrdemInspecao } from '@/hooks/use-ordens-inspecao'
import { opcoesFiltrosExemplo } from '@/mocks/opcoes-filtros'

// DADOS DE EXEMPLO para a Fila de inspeção. Não vêm da base real: as UCs são
// inventadas (UC900001 em diante, fora da faixa da base) e as regras seguem o
// motor de score da Gold (data-engineering/05_gold_perdas.py)

// Gerador de números sempre igual, para a fila não mudar a cada recarga
function sorteador(semente: number) {
  let estado = semente
  return () => {
    estado = (estado * 1_103_515_245 + 12_345) % 2_147_483_648
    return estado / 2_147_483_648
  }
}

const sortear = sorteador(42)
const escolher = <T,>(itens: T[]) => itens[Math.floor(sortear() * itens.length)]

// Bairros com taxa de irregularidade acima de 1,2× a média (inventados)
const BAIRROS_RISCO = ['Ibura', 'Janga', 'Prazeres', 'Rio Doce']

const CLASSES: ClasseConsumo[] = [
  ...Array<ClasseConsumo>(14).fill('RESIDENCIAL'),
  ...Array<ClasseConsumo>(4).fill('COMERCIAL'),
  'INDUSTRIAL',
  'RURAL',
]

function regraDaFaixa<T>(valor: number, faixas: [number, T][]) {
  return faixas.find(([limite]) => valor >= limite)?.[1]
}

function gerarItem(indice: number): Omit<ItemFila, 'prioridade' | 'ordem_aberta'> | undefined {
  const { nome: municipio, bairros } = escolher(opcoesFiltrosExemplo.municipios)
  const bairro = escolher(bairros)
  const classe = escolher(CLASSES)

  // Queda de consumo (%): metade das UCs com queda forte, o resto com queda leve ou nenhuma
  const queda = regraDaFaixa(sortear(), [
    [0.5, sortear() * 15],
    [0.3, 15 + sortear() * 15],
    [0.15, 30 + sortear() * 20],
    [0, 50 + sortear() * 30],
  ])!
  const estimadas = sortear()
  const anomalias = sortear()

  // [regra como a Gold escreve, pontos], só as que dispararam
  const regras: ([string, number] | false)[] = [
    queda >= 50 && ['Queda de consumo >= 50%', 40],
    queda >= 30 && queda < 50 && ['Queda de consumo >= 30%', 30],
    queda >= 15 && queda < 30 && ['Queda de consumo >= 15%', 15],
    sortear() < 0.45 && ['Medidor eletromecanico', 15],
    estimadas < 0.12 && ['Leituras estimadas >= 50%', 15],
    estimadas >= 0.12 && estimadas < 0.3 && ['Leituras estimadas >= 25%', 8],
    anomalias < 0.1 && ['Multiplas anomalias de leitura', 10],
    anomalias >= 0.1 && anomalias < 0.25 && ['Anomalia de leitura recente', 5],
    BAIRROS_RISCO.includes(bairro) && ['Bairro com taxa de irregularidade >= 1.2x', 10],
    sortear() < 0.15 && ['Historico de irregularidade anterior', 10],
    sortear() < 0.08 && ['Inspecionada regular ha <= 180 dias', -25],
  ]
  const motivos = regras.filter((regra) => regra !== false)
  const variacao = -queda

  const score = Math.min(100, Math.max(0, motivos.reduce((soma, [, pontos]) => soma + pontos, 0)))
  if (score < 20) {
    return undefined
  }

  const consumoAnterior = classe === 'RESIDENCIAL' ? 120 + sortear() * 280 : 400 + sortear() * 2400
  const consumoRecente = consumoAnterior * (1 + variacao / 100)

  return {
    id_uc: `UC9${String(indice + 1).padStart(5, '0')}`,
    score,
    motivo_suspeita: motivos.map(([texto, pontos]) => `${texto} (${pontos > 0 ? '+' : ''}${pontos})`).join('; '),
    kwh_recuperavel_estimado_ano: Math.round(Math.max(0, consumoAnterior - consumoRecente) * 12 * 100) / 100,
    municipio,
    bairro,
    classe,
  }
}

// Ordenada como na Gold: maior score e depois maior kWh recuperável
const fila = Array.from({ length: 420 }, (_, indice) => gerarItem(indice))
  .filter((item) => item !== undefined)
  .sort((a, b) => b.score - a.score || b.kwh_recuperavel_estimado_ano - a.kwh_recuperavel_estimado_ano)
  .map((item, posicao) => ({ ...item, prioridade: posicao + 1 }))

// Ordens criadas pela tela, guardadas só na memória do navegador (somem ao recarregar)
let ordens: OrdemInspecao[] = []
let proximaOrdem = 1

const encerrada = (ordem: OrdemInspecao) => ordem.status === 'CONCLUIDA' || ordem.status === 'CANCELADA'

function ordemAberta(idUc: string) {
  return ordens.find((ordem) => ordem.id_uc === idUc && !encerrada(ordem))
}

type FiltrosFila = { municipio?: string | null; bairro?: string | null; classe?: string | null }

export function buscarFila({ municipio, bairro, classe }: FiltrosFila, pagina: number, limite: number): FilaInspecao {
  const recorte = fila.filter(
    (item) =>
      (!municipio || item.municipio === municipio) &&
      (!bairro || item.bairro === bairro) &&
      (!ehClasseConsumo(classe) || item.classe === classe),
  )
  const inicio = (pagina - 1) * limite

  return {
    data_referencia: '2026-06-30',
    resumo: {
      ucs: recorte.length,
      kwh_recuperavel_estimado_ano: recorte.reduce((soma, item) => soma + item.kwh_recuperavel_estimado_ano, 0),
    },
    pagina,
    limite,
    total: recorte.length,
    itens: recorte.slice(inicio, inicio + limite).map((item) => {
      const ordem = ordemAberta(item.id_uc)
      return { ...item, ordem_aberta: ordem ? { id_ordem: ordem.id_ordem, status: ordem.status } : null }
    }),
  }
}

export function listarOrdens() {
  return [...ordens].reverse()
}

// UCs que já têm ordem aberta ou que não estão na fila são ignoradas
export function gerarOrdens(idsUc: string[]) {
  // Hora local no formato da API (yyyy-MM-ddTHH:mm:ss)
  const data = new Date()
  const agora = new Date(data.getTime() - data.getTimezoneOffset() * 60_000).toISOString().slice(0, 19)
  const novas = fila
    .filter((item) => idsUc.includes(item.id_uc) && !ordemAberta(item.id_uc))
    .map(
      (item): OrdemInspecao => ({
        id_ordem: `OI-${String(proximaOrdem++).padStart(5, '0')}`,
        id_uc: item.id_uc,
        municipio: item.municipio,
        bairro: item.bairro,
        status: 'ABERTA',
        resultado: null,
        criada_em: agora,
      }),
    )
  ordens = [...ordens, ...novas]
  return novas
}

// Devolve a mensagem de erro quando a mudança não é permitida
export function mudarOrdem(idOrdem: string, mudanca: MudancaOrdem | { status: 'CANCELADA' }) {
  const ordem = ordens.find((item) => item.id_ordem === idOrdem)
  if (!ordem) {
    return { erro: 'Ordem de inspeção não encontrada.', status: 404 }
  }
  const permitido =
    (mudanca.status === 'EM_CAMPO' && ordem.status === 'ABERTA') ||
    (mudanca.status === 'CONCLUIDA' && ordem.status === 'EM_CAMPO') ||
    (mudanca.status === 'CANCELADA' && !encerrada(ordem))
  if (!permitido) {
    return { erro: 'Essa mudança não vale para a situação atual da ordem.', status: 409 }
  }
  const atualizada: OrdemInspecao = {
    ...ordem,
    status: mudanca.status,
    resultado: mudanca.status === 'CONCLUIDA' ? mudanca.resultado : null,
  }
  ordens = ordens.map((item) => (item.id_ordem === idOrdem ? atualizada : item))
  return { ordem: atualizada }
}

// Para os testes começarem sempre sem ordens
export function limparOrdens() {
  ordens = []
  proximaOrdem = 1
}
