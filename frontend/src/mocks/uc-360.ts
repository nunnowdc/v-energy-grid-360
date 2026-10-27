import type { Uc360 } from '@/hooks/use-uc-360'

// DADOS DE EXEMPLO de GET /api/uc/{id}/360, para os testes. Tudo inventado:
// nenhum nome, endereço ou valor vem da base real
const meses = ['2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12', '2026-01', '2026-02', '2026-03', '2026-04', '2026-05', '2026-06']

export const uc360Exemplo: Uc360 = {
  uc: {
    id_uc: 'UC000001',
    nome_titular: 'Maria Exemplo da Silva',
    logradouro: 'Rua de Exemplo',
    numero: '100',
    bairro: 'Boa Viagem',
    municipio: 'Recife',
    uf: 'PE',
    classe: 'RESIDENCIAL',
  },
  medidor_atual: {
    id_medidor_atual: 'MD000001',
    tipo_medidor_atual: 'ELETROMECANICO',
    modelo_medidor_atual: 'EX-100',
    data_instalacao_medidor_atual: '2015-03-10',
  },
  geracao_distribuida: { possui_gd: true, data_conexao_gd: '2024-02-01', potencia_gd_kwp: 4.5, modalidade_gd: 'GERACAO NA PROPRIA UC' },
  faturas_em_aberto: [
    { id_fatura: 'FT000001', mes_referencia: '2026-01', data_vencimento: '2026-01-25', receita_faturada: 210.5, status_pagamento: 'ATRASADA' },
    { id_fatura: 'FT000002', mes_referencia: '2026-06', data_vencimento: '2026-07-05', receita_faturada: 180, status_pagamento: 'PENDENTE' },
  ],
  resumo_faturas_em_aberto: { quantidade: 2, valor_total: 390.5 },
  consumo_12m: meses.map((mes, indice) => ({
    mes_referencia: mes,
    consumo_kwh: 200 + indice * 5,
    consumo_ano_anterior_kwh: 210,
    variacao_ano_anterior_pct: ((200 + indice * 5 - 210) / 210) * 100,
  })),
  historicos: {
    faturas: {
      pagina: 1,
      limite: 10,
      total: 1,
      itens: [
        {
          id_fatura: 'FT000002',
          mes_referencia: '2026-06',
          consumo_kwh: 255,
          bandeira_tarifaria: 'AMARELA',
          receita_faturada: 180,
          data_vencimento: '2026-07-05',
          status_pagamento: 'PENDENTE',
          data_emissao: '2026-06-20',
          data_pagamento: null,
          dias_atraso: null,
        },
      ],
    },
    leituras: { pagina: 1, limite: 10, total: 0, itens: [] },
    interrupcoes: {
      pagina: 1,
      limite: 10,
      total: 1,
      itens: [
        {
          id_ocorrencia: 'OC000001',
          alimentador: 'ALM-REC-001',
          tipo: 'FALTA DE ENERGIA',
          causa: 'VEGETACAO',
          data_abertura: '2026-03-02T10:00:00',
          data_encerramento: '2026-03-02T12:30:00',
          duracao_h: 2.5,
          duracao_truncada: false,
        },
      ],
    },
    chamados: { pagina: 1, limite: 10, total: 0, itens: [] },
  },
}
