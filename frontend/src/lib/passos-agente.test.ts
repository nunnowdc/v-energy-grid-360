import { describe, expect, test } from 'vitest'
import { lerListaPassos, montarPassos } from '@/lib/passos-agente'

describe('lerListaPassos', () => {
  test('lê o texto JSON da auditoria e aceita a lista pronta', () => {
    expect(lerListaPassos('["Nó 1 — a", "Nó 2 — b"]')).toEqual(['Nó 1 — a', 'Nó 2 — b'])
    expect(lerListaPassos(['Nó 1 — a'])).toEqual(['Nó 1 — a'])
  })

  test('texto vazio ou inválido vira lista vazia', () => {
    expect(lerListaPassos(null)).toEqual([])
    expect(lerListaPassos('não é JSON')).toEqual([])
    expect(lerListaPassos('{"a": 1}')).toEqual([])
  })
})

describe('montarPassos', () => {
  // Caminho real de uma pergunta respondida pela consulta certificada
  const certificada = [
    'Nó 1 — Filtro de segurança: aprovado.',
    'Nó 2 — Follow-up: sem histórico, pergunta original mantida (0 chamadas LLM).',
    "Nó 4 — Roteador: 'sql' (confiança 99%). Requer consulta de valores faturados.",
    'Nó 6 — Cache certificado: faturamento_por_municipio_ano (olinda, 2023).',
    'Nó 9 — Execução SQL OK. 1 linha(s) em 121ms.',
    'Nó 11 — Síntese gerada. Selo: certificada. 1 linha(s) de dados utilizadas.',
    'Nó 11 — Conferência numérica reprovada; resposta determinística utilizada.',
  ]

  test('tira o número e o rótulo que repete o nome do nó', () => {
    const [filtro, contexto, roteador] = montarPassos(certificada)
    expect(filtro).toMatchObject({ no: 1, detalhes: ['Aprovado.'], situacao: 'concluido' })
    expect(contexto.detalhes).toEqual(['Sem histórico, pergunta original mantida (0 chamadas LLM).'])
    expect(roteador.detalhes).toEqual(["'sql' (confiança 99%). Requer consulta de valores faturados."])
  })

  test('mantém o texto quando o rótulo tem informação', () => {
    const [passo] = montarPassos(['Nó 7 — SQL escrito (tentativa 2): SELECT 1...'])
    expect(passo.detalhes).toEqual(['SQL escrito (tentativa 2): SELECT 1...'])
  })

  test('junta linhas seguidas do mesmo nó', () => {
    const passos = montarPassos(certificada)
    expect(passos.map((passo) => passo.no)).toEqual([1, 2, 4, 6, 9, 11])
    expect(passos.at(-1)).toMatchObject({
      detalhes: [
        'Síntese gerada. Selo: certificada. 1 linha(s) de dados utilizadas.',
        'Conferência numérica reprovada; resposta determinística utilizada.',
      ],
      situacao: 'atencao',
    })
  })

  test('marca a volta a um nó anterior como nova tentativa', () => {
    const passos = montarPassos([
      'Nó 7 — SQL escrito (tentativa 1): SELECT x...',
      'Nó 8 — Validação aprovada. Tabelas identificadas: [\'agg\']',
      'Nó 9 — Erro na execução (tentativa 1): coluna x não existe',
      'Nó 7 — SQL escrito (tentativa 2): SELECT y...',
    ])
    expect(passos.map((passo) => [passo.no, passo.situacao, passo.repeticao])).toEqual([
      [7, 'concluido', false],
      [8, 'concluido', false],
      [9, 'atencao', false],
      [7, 'concluido', true],
    ])
  })

  test('passos que levam à recusa ficam como interrompidos', () => {
    const passos = montarPassos([
      'Nó 1 — Filtro de segurança: aprovado.',
      'Nó 3 — Escopo LLM: fora (Pergunta genérica sem relação com a distribuidora)',
      'Nó 10 — Recusa emitida: fora_escopo.',
    ])
    expect(passos.map((passo) => passo.situacao)).toEqual(['concluido', 'interrompido', 'interrompido'])
  })

  test('busca sem resultado e consulta não encontrada pedem atenção', () => {
    const passos = montarPassos([
      'Nó 5 — RAG: 0 chunks recuperados (abaixo do limiar). Rota: sql.',
      'Nó 6 — Cache: miss (slots ou intenção não identificados).',
    ])
    expect(passos.map((passo) => passo.situacao)).toEqual(['atencao', 'atencao'])
  })

  test('texto fora do padrão vira um passo sem número', () => {
    expect(montarPassos(['Erro crítico na execução do grafo.'])).toEqual([
      { no: null, detalhes: ['Erro crítico na execução do grafo.'], situacao: 'interrompido', repeticao: false },
    ])
  })
})
