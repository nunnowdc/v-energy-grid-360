import { classesConsumo, type ClasseConsumo } from '@/config/classes'
import { rotuloCausa } from '@/config/causas'
import type { DashboardAgente } from '@/hooks/use-agente-ia'
import type { OpcoesFiltros } from '@/hooks/use-opcoes-filtros'
import { formatarPeriodo } from '@/lib/formatacao'
import { comparacaoDoPeriodo, type Periodo } from '@/lib/periodos'

// Tela do dashboard que mostra o assunto de uma resposta do agente
export type TelaDaResposta = {
  // Endereço com os filtros, ex.: "/?municipio=Recife"
  caminho: string
  // Valores aplicados, como aparecem na tela, ex.: ["Recife", "Residencial"]
  filtros: string[]
}

type CampoTexto = 'municipio' | 'bairro' | 'classe' | 'alimentador' | 'causa'
// 'comparacao': a tela tem "Período base" e "Comparado com"
type CampoFiltro = 'comparacao' | CampoTexto
type Valores = Partial<Record<CampoTexto, string | null>> & {
  periodo?: Periodo | null
  periodo_base?: Periodo | null
}

// Na ordem de prioridade: "maior DEC do alimentador" é Continuidade, mesmo
// falando de consumo. O assunto só serve para respostas sem consulta (glossário,
// normas); com consulta, quem decide a tela é o agente, pelas tabelas usadas
const telas: { tela: DashboardAgente['tela']; to: string; campos: CampoFiltro[]; assunto: RegExp }[] = [
  {
    tela: 'continuidade',
    to: '/continuidade',
    campos: ['comparacao', 'municipio', 'alimentador', 'causa'],
    assunto: /\b(dec|fec)\b|continuidade|interrup|ocorrencia|alimentador|queda de (luz|energia)|falta de (luz|energia)/,
  },
  {
    tela: 'inspecoes',
    to: '/inspecoes',
    campos: ['municipio', 'bairro', 'classe'],
    assunto: /suspeit|fraude|inspec|perdas? nao tecnica|desvio de energia|\bgatos?\b/,
  },
  {
    // Receita mostra a variação; a receita de cada mês está nos Indicadores
    tela: 'receita',
    to: '/receita',
    campos: ['comparacao', 'municipio', 'bairro', 'classe'],
    assunto: /efeito (preco|volume)|variacao d[ae] receita|ponte da receita|preco medio|tarifa/,
  },
  {
    tela: 'indicadores',
    to: '/',
    campos: ['comparacao', 'municipio', 'classe'],
    assunto: /fatura|receita|consumo|kwh|unidades? consumidoras?|\bucs\b|inadimpl|indicador/,
  },
]

// Plural e feminino entram: "residenciais", "comerciais", "rurais"
const sinaisClasse: Record<ClasseConsumo, RegExp> = {
  RESIDENCIAL: /\bresidenc/,
  COMERCIAL: /\bcomerc/,
  INDUSTRIAL: /\bindustri/,
  RURAL: /\brura(l|is)\b/,
  PODER_PUBLICO: /poder(es)? public/,
}

// Minúsculas e sem acento: "Jaboatão" casa com "jaboatao" e com 'JABOATAO'
function normalizar(texto: string) {
  return texto.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase()
}

// Para comparar valores: "poder publico" é o mesmo que "PODER_PUBLICO"
const chave = (texto: string) => normalizar(texto).replace(/[\s_]+/g, ' ').trim()

// O nome da lista igual ao valor, ignorando maiúsculas, acentos e espaços
function igual<T extends string>(valor: string | null | undefined, nomes: readonly T[]): T | undefined {
  return valor ? nomes.find((nome) => chave(nome) === chave(valor)) : undefined
}

const escapar = (texto: string) => texto.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

// O nome inteiro aparece no texto (não dentro de outra palavra)
const menciona = (texto: string, nome: string) =>
  new RegExp(`(^|[^a-z0-9])${escapar(normalizar(nome))}([^a-z0-9]|$)`).test(texto)

// Com mais de um nome citado vale o mais longo ("Cabo de Santo Agostinho", não "Cabo")
function maisLongoMencionado(texto: string, nomes: string[]): string | undefined {
  return nomes.filter((nome) => menciona(texto, nome)).sort((a, b) => b.length - a.length)[0]
}

const UC = /\buc\d{6}\b/i
const ALIMENTADOR = /\balm-[a-z]{3}-\d{3}\b/

function visao360(idUc: string): TelaDaResposta {
  const id = idUc.toUpperCase()
  return { caminho: `/visao-360/${id}`, filtros: [id] }
}

// Monta o endereço com os valores que existem nas opções e que a tela tem.
// Sem as opções carregadas, abre a tela sem filtros
function montar(tela: (typeof telas)[number], valores: Valores, opcoes?: OpcoesFiltros): TelaDaResposta {
  const params = new URLSearchParams()
  const filtros: string[] = []
  function aplicar(campo: CampoTexto, valor: string | undefined, rotulo = valor) {
    if (valor && tela.campos.includes(campo)) {
      params.set(campo, valor)
      filtros.push(rotulo!)
    }
  }

  if (opcoes) {
    const alimentador = tela.campos.includes('alimentador')
      ? igual(valores.alimentador, opcoes.alimentadores.map(({ codigo }) => codigo))
      : undefined
    const atendidos = opcoes.alimentadores.find(({ codigo }) => codigo === alimentador)?.municipios

    let municipio = igual(valores.municipio, opcoes.municipios.map(({ nome }) => nome))
    // Bairro sem município: vale se o nome existe num município só
    // ("Jardim Primavera" é de Camaragibe; "Centro" há em vários)
    if (!valores.municipio && valores.bairro) {
      const comOBairro = opcoes.municipios.filter(({ bairros }) => igual(valores.bairro, bairros))
      municipio = comOBairro.length === 1 ? comOBairro[0].nome : undefined
    }
    // O município fica só se o alimentador o atende
    if (atendidos && municipio && !atendidos.includes(municipio)) {
      municipio = undefined
    }
    aplicar('municipio', municipio)

    // O bairro só vale dentro do município (há "Centro" em vários) e quando
    // não é o próprio nome do município
    const bairros = opcoes.municipios.find(({ nome }) => nome === municipio)?.bairros ?? []
    aplicar('bairro', igual(valores.bairro, bairros.filter((bairro) => chave(bairro) !== chave(municipio ?? ''))))

    const classe = igual(valores.classe, opcoes.classes)
    aplicar('classe', classe, classe && classesConsumo[classe].label)

    aplicar('alimentador', alimentador)

    const causa = igual(valores.causa, opcoes.causas)
    aplicar('causa', causa, causa && rotuloCausa(causa))

    // O período consultado vai para o "Comparado com", que é o que os KPIs mostram;
    // o base fica com os mesmos meses do ano anterior, se a consulta não comparou dois
    const comparacao =
      tela.campos.includes('comparacao') && valores.periodo
        ? comparacaoDoPeriodo(opcoes.competencias, valores.periodo, valores.periodo_base ?? undefined)
        : undefined
    if (comparacao) {
      const { base, comparado } = comparacao
      params.set('base_de', base.de)
      params.set('base_ate', base.ate)
      params.set('comparado_de', comparado.de)
      filtros.push(
        `${formatarPeriodo(comparado.de, comparado.ate)} comparado com ${formatarPeriodo(base.de, base.ate)}`,
      )
    }
  }

  const busca = params.toString()
  return { caminho: busca ? `${tela.to}?${busca}` : tela.to, filtros }
}

// Tela e filtros que o agente escolheu pelas tabelas e pelo WHERE da consulta.
// Os valores vêm como estão no SQL ("recife") e viram os nomes das opções ("Recife")
export function telaDoAgente(dashboard: DashboardAgente, opcoes?: OpcoesFiltros): TelaDaResposta | null {
  if (dashboard.tela === 'visao_360') {
    const idUc = dashboard.filtros.id_uc
    return idUc && UC.test(idUc) ? visao360(idUc) : null
  }
  const tela = telas.find((item) => item.tela === dashboard.tela)
  return tela ? montar(tela, dashboard.filtros, opcoes) : null
}

// Para respostas sem consulta: a tela vem do assunto da pergunta e os filtros,
// dos nomes citados nela. Sem assunto reconhecido, devolve null
export function telaDaPergunta(pergunta: string, opcoes?: OpcoesFiltros): TelaDaResposta | null {
  const texto = normalizar(pergunta)

  const uc = UC.exec(texto)?.[0]
  if (uc) {
    return visao360(uc)
  }

  const tela = telas.find(({ assunto }) => assunto.test(texto))
  if (!tela) {
    return null
  }

  const municipio = opcoes && maisLongoMencionado(texto, opcoes.municipios.map(({ nome }) => nome))
  const bairros = opcoes?.municipios.find(({ nome }) => nome === municipio)?.bairros ?? []
  return montar(
    tela,
    {
      municipio,
      bairro: maisLongoMencionado(texto, bairros),
      classe: opcoes?.classes.find((codigo) => sinaisClasse[codigo]?.test(texto)),
      alimentador: ALIMENTADOR.exec(texto)?.[0],
      causa: opcoes?.causas.find((codigo) => menciona(texto, codigo) || menciona(texto, rotuloCausa(codigo))),
    },
    opcoes,
  )
}
