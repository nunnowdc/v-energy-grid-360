import { useQuery } from '@tanstack/react-query'
import type { BandeiraTarifaria } from '@/config/bandeiras'
import type { ClasseConsumo } from '@/config/classes'
import { apiFetch } from '@/lib/api/api-fetch'

// Formato de GET /api/uc/{uc_id}/360, igual ao backend/app/schemas/uc.py.
// Datas chegam como "yyyy-MM-dd" e datas com hora como "yyyy-MM-ddTHH:mm:ss"

export type StatusPagamento = 'PAGA' | 'PENDENTE' | 'ATRASADA'

type Pagina<T> = {
  pagina: number
  limite: number
  total: number
  itens: T[]
}

export type FaturaUc = {
  id_fatura: string
  mes_referencia: string
  consumo_kwh: number | null
  bandeira_tarifaria: BandeiraTarifaria | null
  receita_faturada: number | null
  data_vencimento: string | null
  status_pagamento: StatusPagamento | null
  data_emissao: string | null
  data_pagamento: string | null
  dias_atraso: number | null
}

export type LeituraUc = {
  id_leitura: string
  id_medidor: string | null
  mes_referencia: string
  data_leitura: string | null
  leitura_anterior: number | null
  leitura_atual: number | null
  consumo_kwh: number | null
  consumo_ano_anterior_kwh: number | null
  variacao_ano_anterior_pct: number | null
  tipo_leitura: string | null
  status_qualidade_leitura: string | null
  consumo_imputado: boolean | null
}

export type InterrupcaoUc = {
  id_ocorrencia: string
  alimentador: string | null
  tipo: string | null
  causa: string | null
  data_abertura: string | null
  data_encerramento: string | null
  duracao_h: number | null
  // Duração cortada em 48 h na Gold
  duracao_truncada: boolean | null
}

export type ChamadoUc = {
  protocolo: string
  assunto: string | null
  subassunto: string | null
  canal: string | null
  data_abertura: string | null
  data_fechamento: string | null
  status_chamado: string | null
  qtd_tratativas: number | null
}

export type ConsumoMes = {
  mes_referencia: string
  consumo_kwh: number | null
  consumo_ano_anterior_kwh: number | null
  variacao_ano_anterior_pct: number | null
}

export type Uc360 = {
  uc: {
    id_uc: string
    nome_titular: string | null
    logradouro: string | null
    numero: string | null
    bairro: string | null
    municipio: string | null
    uf: string | null
    classe: ClasseConsumo | null
  }
  medidor_atual: {
    id_medidor_atual: string
    tipo_medidor_atual: string | null
    modelo_medidor_atual: string | null
    data_instalacao_medidor_atual: string | null
  } | null
  geracao_distribuida: {
    possui_gd: boolean | null
    data_conexao_gd: string | null
    potencia_gd_kwp: number | null
    modalidade_gd: string | null
  }
  faturas_em_aberto: {
    id_fatura: string
    mes_referencia: string
    data_vencimento: string | null
    receita_faturada: number | null
    status_pagamento: StatusPagamento | null
  }[]
  resumo_faturas_em_aberto: { quantidade: number; valor_total: number | null }
  consumo_12m: ConsumoMes[]
  historicos: {
    faturas: Pagina<FaturaUc>
    interrupcoes: Pagina<InterrupcaoUc>
    chamados: Pagina<ChamadoUc>
    leituras: Pagina<LeituraUc>
  }
}

export type HistoricoUc = keyof Uc360['historicos']

// Página atual de cada histórico (começa em 1)
export type PaginasHistorico = Record<HistoricoUc, number>

export const PAGINAS_INICIAIS: PaginasHistorico = { faturas: 1, leituras: 1, interrupcoes: 1, chamados: 1 }

// Linhas por página nas tabelas de histórico (o backend aceita até 50)
export const LIMITE_HISTORICO = 10

// O ID da UC na Gold é "UC" + 6 números, ex.: UC100000
const FORMATO_ID_UC = /^UC\d{6}$/

export function ehIdUc(valor: string) {
  return FORMATO_ID_UC.test(valor)
}

export function useUc360(idUc: string | undefined, paginas: PaginasHistorico) {
  return useQuery({
    queryKey: ['uc-360', idUc, paginas],
    queryFn: ({ signal }) => {
      const params = new URLSearchParams({
        pagina_faturas: String(paginas.faturas),
        pagina_leituras: String(paginas.leituras),
        pagina_interrupcoes: String(paginas.interrupcoes),
        pagina_chamados: String(paginas.chamados),
        limite: String(LIMITE_HISTORICO),
      })
      return apiFetch<Uc360>(`/uc/${idUc}/360?${params}`, { signal })
    },
    // ID fora do formato nem chega a ser buscado
    enabled: idUc !== undefined && ehIdUc(idUc),
    // Ao trocar de página, a tabela anterior fica na tela até a nova chegar.
    // Só para a mesma UC: outra UC nunca mostra os dados da anterior
    placeholderData: (anterior, consultaAnterior) =>
      consultaAnterior?.queryKey[1] === idUc ? anterior : undefined,
  })
}
