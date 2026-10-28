import { describe, expect, test } from 'vitest'
import { telaDaPergunta, telaDoAgente } from '@/lib/tela-da-resposta'
import { opcoesFiltrosExemplo as opcoes } from '@/mocks/opcoes-filtros'

describe('com consulta, a tela vem do agente', () => {
  test('os valores do SQL viram os nomes das opções', () => {
    expect(telaDoAgente({ tela: 'indicadores', filtros: { municipio: 'recife', classe: 'residencial' } }, opcoes)).toEqual(
      { caminho: '/?municipio=Recife&classe=RESIDENCIAL', filtros: ['Recife', 'Residencial'] },
    )
    expect(
      telaDoAgente(
        { tela: 'receita', filtros: { municipio: 'JABOATAO DOS GUARARAPES', bairro: 'piedade', classe: 'poder publico' } },
        opcoes,
      ),
    ).toEqual({
      caminho: '/receita?municipio=Jaboat%C3%A3o+dos+Guararapes&bairro=Piedade&classe=PODER_PUBLICO',
      filtros: ['Jaboatão dos Guararapes', 'Piedade', 'Poder público'],
    })
  })

  test('alimentador e causa entram na Continuidade', () => {
    expect(
      telaDoAgente({ tela: 'continuidade', filtros: { alimentador: 'alm-rec-001', causa: 'vegetacao' } }, opcoes),
    ).toEqual({ caminho: '/continuidade?alimentador=ALM-REC-001&causa=VEGETACAO', filtros: ['ALM-REC-001', 'Vegetação'] })
  })

  test('cada tela recebe só os filtros que ela tem', () => {
    // Os Indicadores não filtram por bairro nem alimentador
    expect(
      telaDoAgente(
        { tela: 'indicadores', filtros: { municipio: 'Recife', bairro: 'Pina', alimentador: 'ALM-OLI-001' } },
        opcoes,
      )?.caminho,
    ).toBe('/?municipio=Recife')
  })

  test('valor que não existe nas opções fica de fora', () => {
    expect(
      telaDoAgente({ tela: 'receita', filtros: { municipio: 'Recif', bairro: 'Piedade', classe: 'MISTA' } }, opcoes),
    ).toEqual({ caminho: '/receita', filtros: [] })
    // O bairro só vale dentro do município
    expect(telaDoAgente({ tela: 'receita', filtros: { municipio: 'Recife', bairro: 'Piedade' } }, opcoes)?.caminho).toBe(
      '/receita?municipio=Recife',
    )
  })

  test('bairro sem município leva o município, se o nome só existe em um', () => {
    expect(telaDoAgente({ tela: 'receita', filtros: { bairro: 'boa viagem' } }, opcoes)).toEqual({
      caminho: '/receita?municipio=Recife&bairro=Boa+Viagem',
      filtros: ['Recife', 'Boa Viagem'],
    })
    // Com o mesmo bairro em dois municípios, não dá para saber qual
    const comBairroRepetido = {
      ...opcoes,
      municipios: [...opcoes.municipios, { nome: 'Moreno', bairros: ['Boa Viagem'] }],
    }
    expect(telaDoAgente({ tela: 'receita', filtros: { bairro: 'Boa Viagem' } }, comBairroRepetido)?.caminho).toBe(
      '/receita',
    )
  })

  test('o município sai se o alimentador não o atende', () => {
    expect(
      telaDoAgente({ tela: 'continuidade', filtros: { municipio: 'Recife', alimentador: 'ALM-OLI-001' } }, opcoes)?.caminho,
    ).toBe('/continuidade?alimentador=ALM-OLI-001')
  })

  test('a Visão 360 abre na UC da consulta', () => {
    expect(telaDoAgente({ tela: 'visao_360', filtros: { id_uc: 'uc100000' } }, opcoes)).toEqual({
      caminho: '/visao-360/UC100000',
      filtros: ['UC100000'],
    })
    expect(telaDoAgente({ tela: 'visao_360', filtros: {} }, opcoes)).toBeNull()
  })

  test('sem as opções carregadas, abre a tela sem filtros', () => {
    expect(telaDoAgente({ tela: 'inspecoes', filtros: { municipio: 'Olinda' } })).toEqual({
      caminho: '/inspecoes',
      filtros: [],
    })
  })
})

describe('sem consulta, a tela vem do assunto da pergunta', () => {
  test('DEC e FEC abrem a Continuidade, mesmo sem filtro', () => {
    expect(telaDaPergunta('O que é DEC e FEC?', opcoes)).toEqual({ caminho: '/continuidade', filtros: [] })
  })

  test('efeito preço abre a Receita; faturamento e consumo, os Indicadores', () => {
    expect(telaDaPergunta('O que é efeito preço?', opcoes)?.caminho).toBe('/receita')
    expect(telaDaPergunta('Como é calculado o faturamento em Recife?', opcoes)?.caminho).toBe('/?municipio=Recife')
    expect(telaDaPergunta('O que conta como consumo residencial?', opcoes)?.caminho).toBe('/?classe=RESIDENCIAL')
  })

  test('suspeita de fraude abre a Fila, com os nomes citados', () => {
    expect(telaDaPergunta('Como uma UC vira suspeita de fraude em Jaboatao dos Guararapes, em Piedade?', opcoes)).toEqual({
      caminho: '/inspecoes?municipio=Jaboat%C3%A3o+dos+Guararapes&bairro=Piedade',
      filtros: ['Jaboatão dos Guararapes', 'Piedade'],
    })
  })

  test('alimentador e causa citados entram na Continuidade', () => {
    expect(telaDaPergunta('Por que vegetação derruba o alimentador ALM-REC-001?', opcoes)?.caminho).toBe(
      '/continuidade?alimentador=ALM-REC-001&causa=VEGETACAO',
    )
  })

  test('uma UC citada abre a Visão 360 dela', () => {
    expect(telaDaPergunta('A uc129001 tem fatura atrasada?', opcoes)?.caminho).toBe('/visao-360/UC129001')
  })

  test('sem assunto reconhecido, o dashboard fica como está', () => {
    expect(telaDaPergunta('Bom dia, tudo bem?', opcoes)).toBeNull()
  })
})
