import { describe, expect, test } from 'vitest'
import { telaDaResposta } from '@/lib/tela-da-resposta'
import { opcoesFiltrosExemplo as opcoes } from '@/mocks/opcoes-filtros'

describe('a tela vem do assunto da pergunta', () => {
  test('faturamento abre a Receita do município citado', () => {
    expect(telaDaResposta({ pergunta: 'Qual o faturamento em Recife no ano de 2024?', opcoes })).toEqual({
      caminho: '/receita?municipio=Recife',
      filtros: ['Recife'],
    })
  })

  test('DEC e FEC abrem a Continuidade, mesmo sem filtro', () => {
    expect(telaDaResposta({ pergunta: 'O que é DEC e FEC?', opcoes })).toEqual({
      caminho: '/continuidade',
      filtros: [],
    })
  })

  test('UC suspeita abre a Fila; consumo e unidades abrem os Indicadores', () => {
    expect(telaDaResposta({ pergunta: 'Quais UCs suspeitas de fraude em Olinda?', opcoes })?.caminho).toBe(
      '/inspecoes?municipio=Olinda',
    )
    expect(telaDaResposta({ pergunta: 'Quantas unidades consumidoras existem por classe de consumo?', opcoes })).toEqual(
      { caminho: '/', filtros: [] },
    )
  })

  test('uma UC citada abre a Visão 360 dela', () => {
    expect(telaDaResposta({ pergunta: 'A uc129001 tem fatura atrasada?', opcoes })).toEqual({
      caminho: '/visao-360/UC129001',
      filtros: ['UC129001'],
    })
  })

  test('sem assunto na pergunta, a consulta decide pela tabela', () => {
    expect(
      telaDaResposta({
        pergunta: 'E em 2023?',
        sql: "SELECT SUM(r.receita_faturada) FROM agg_receita_mensal r WHERE unaccent(lower(r.municipio)) = unaccent(lower('olinda'))",
        opcoes,
      })?.caminho,
    ).toBe('/receita?municipio=Olinda')
  })

  test('sem assunto reconhecido, o dashboard fica como está', () => {
    expect(telaDaResposta({ pergunta: 'Bom dia, tudo bem?', opcoes })).toBeNull()
  })
})

describe('os filtros aparecem como na tela', () => {
  test('sem acento, em maiúsculas ou no plural', () => {
    expect(
      telaDaResposta({ pergunta: 'Receita das UCS RESIDENCIAIS de jaboatao dos guararapes em Piedade', opcoes }),
    ).toEqual({
      caminho: '/receita?municipio=Jaboat%C3%A3o+dos+Guararapes&bairro=Piedade&classe=RESIDENCIAL',
      filtros: ['Jaboatão dos Guararapes', 'Piedade', 'Residencial'],
    })
  })

  test('cada tela recebe só os filtros que ela tem', () => {
    // A Continuidade não filtra por classe nem bairro; os Indicadores não filtram por bairro
    expect(telaDaResposta({ pergunta: 'Interrupções comerciais em Boa Viagem, Recife', opcoes })?.caminho).toBe(
      '/continuidade?municipio=Recife',
    )
    expect(telaDaResposta({ pergunta: 'Consumo comercial em Boa Viagem, Recife', opcoes })?.caminho).toBe(
      '/?municipio=Recife&classe=COMERCIAL',
    )
  })

  test('o bairro só vale dentro do município citado', () => {
    expect(telaDaResposta({ pergunta: 'Receita de Piedade', opcoes })?.caminho).toBe('/receita')
  })

  test('alimentador e causa entram na Continuidade', () => {
    expect(
      telaDaResposta({ pergunta: 'Quantas interrupções por vegetação no ALM-REC-001 em Recife?', opcoes }),
    ).toEqual({
      caminho: '/continuidade?municipio=Recife&alimentador=ALM-REC-001&causa=VEGETACAO',
      filtros: ['Recife', 'ALM-REC-001', 'Vegetação'],
    })
  })

  test('o município sai se o alimentador citado não o atende', () => {
    expect(telaDaResposta({ pergunta: 'DEC do ALM-OLI-001 em Recife', opcoes })?.caminho).toBe(
      '/continuidade?alimentador=ALM-OLI-001',
    )
  })

  test('sem as opções carregadas, abre a tela sem filtros', () => {
    expect(telaDaResposta({ pergunta: 'Qual o faturamento em Recife?' })?.caminho).toBe('/receita')
  })
})

describe('o resultado que só aparece na resposta', () => {
  test('"qual alimentador teve o maior DEC" abre a Continuidade nele', () => {
    expect(
      telaDaResposta({
        pergunta: 'Qual alimentador teve o maior DEC em 2025?',
        sql: 'SELECT alimentador FROM agg_continuidade_alimentador_anual WHERE ano = 2025 ORDER BY dec DESC LIMIT 1',
        resposta: 'Com base nos dados disponíveis, a consulta retornou: alimentador: ALM-JAB-002.',
        opcoes,
      })?.caminho,
    ).toBe('/continuidade?alimentador=ALM-JAB-002')
  })

  test('na resposta vale o primeiro município citado, não o mais longo', () => {
    expect(
      telaDaResposta({
        pergunta: 'Qual município teve o maior faturamento?',
        resposta: '1. Recife: R$ 68 mi\n2. Jaboatão dos Guararapes: R$ 20 mi',
        opcoes,
      })?.caminho,
    ).toBe('/receita?municipio=Recife')
  })

  test('a pergunta tem prioridade sobre a resposta', () => {
    expect(
      telaDaResposta({ pergunta: 'Faturamento de Olinda', resposta: 'Olinda fica atrás de Recife.', opcoes })?.caminho,
    ).toBe('/receita?municipio=Olinda')
  })
})
