import { classesConsumo, type ClasseConsumo } from '@/config/classes'
import { rotuloCausa } from '@/config/causas'
import type { OpcoesFiltros } from '@/hooks/use-opcoes-filtros'

// Tela do dashboard que mostra o assunto de uma resposta do agente
export type TelaDaResposta = {
  // Endereço com os filtros, ex.: "/receita?municipio=Recife"
  caminho: string
  // Valores aplicados, como aparecem na tela, ex.: ["Recife", "Residencial"]
  filtros: string[]
}

type CampoFiltro = 'municipio' | 'bairro' | 'classe' | 'alimentador' | 'causa'

// Na ordem de prioridade: "maior DEC do alimentador" é Continuidade, mesmo
// falando de consumo. O assunto vem da pergunta; sem ele, das tabelas da consulta
const telas: { to: string; campos: CampoFiltro[]; assunto: RegExp; tabelas: RegExp }[] = [
  {
    to: '/continuidade',
    campos: ['municipio', 'alimentador', 'causa'],
    assunto: /\b(dec|fec)\b|continuidade|interrup|ocorrencia|alimentador|queda de (luz|energia)|falta de (luz|energia)/,
    tabelas: /agg_continuidade|fact_ocorrencias/,
  },
  {
    to: '/inspecoes',
    campos: ['municipio', 'bairro', 'classe'],
    assunto: /suspeit|fraude|inspec|perdas? nao tecnica|desvio de energia|\bgatos?\b/,
    tabelas: /fila_inspecao|fact_inspecoes/,
  },
  {
    to: '/receita',
    campos: ['municipio', 'bairro', 'classe'],
    assunto: /fatura(mento|do|da)\b|receita|efeito (preco|volume)|tarifa/,
    tabelas: /agg_receita|fact_faturamento/,
  },
  {
    to: '/',
    campos: ['municipio', 'classe'],
    assunto: /consumo|kwh|unidades? consumidoras?|\bucs\b|inadimpl|indicador/,
    tabelas: /dim_unidade_consumidora|fact_leituras|agg_consumo/,
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

const escapar = (texto: string) => texto.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

// Posição do nome inteiro no texto (não dentro de outra palavra), ou -1
function posicao(texto: string, nome: string) {
  const achado = new RegExp(`(^|[^a-z0-9])${escapar(normalizar(nome))}([^a-z0-9]|$)`).exec(texto)
  return achado ? achado.index : -1
}

const menciona = (texto: string, nome: string) => posicao(texto, nome) >= 0

// Na pergunta, com mais de um nome vale o mais longo ("Cabo de Santo Agostinho", não "Cabo")
function maisLongoMencionado(texto: string, nomes: string[]): string | undefined {
  return nomes.filter((nome) => menciona(texto, nome)).sort((a, b) => b.length - a.length)[0]
}

// Na resposta vale o primeiro citado, que costuma ser o primeiro do ranking
function primeiroMencionado(texto: string, nomes: string[]): string | undefined {
  return nomes
    .map((nome) => ({ nome, onde: posicao(texto, nome) }))
    .filter(({ onde }) => onde >= 0)
    .sort((a, b) => a.onde - b.onde)[0]?.nome
}

const UC = /\buc\d{6}\b/
const ALIMENTADOR = /\balm-[a-z]{3}-\d{3}\b/

type Entrada = {
  pergunta: string
  sql?: string | null
  // Texto da resposta: de onde vem o resultado de "qual alimentador teve o maior DEC?"
  resposta?: string
  // Sem as opções dos filtros, só dá para achar a tela e a UC
  opcoes?: OpcoesFiltros
}

// Lê a pergunta, a consulta e a resposta do agente e decide qual tela do
// dashboard abrir e com quais filtros. Sem assunto reconhecido, devolve null.
// Os filtros vêm da pergunta e da consulta; município, alimentador e UC também
// podem vir da resposta, quando a pergunta não cita nenhum
export function telaDaResposta({ pergunta, sql, resposta, opcoes }: Entrada): TelaDaResposta | null {
  const textoPergunta = normalizar(pergunta)
  const texto = `${textoPergunta} ${normalizar(sql ?? '')}`
  const textoResposta = normalizar(resposta ?? '')

  const uc = (UC.exec(texto) ?? UC.exec(textoResposta))?.[0]
  if (uc) {
    const idUc = uc.toUpperCase()
    return { caminho: `/visao-360/${idUc}`, filtros: [idUc] }
  }

  const tela =
    telas.find(({ assunto }) => assunto.test(textoPergunta)) ??
    telas.find(({ tabelas }) => tabelas.test(texto))
  if (!tela) {
    return null
  }

  const params = new URLSearchParams()
  const filtros: string[] = []
  function aplicar(campo: CampoFiltro, valor: string | undefined, rotulo = valor) {
    if (valor && tela!.campos.includes(campo)) {
      params.set(campo, valor)
      filtros.push(rotulo!)
    }
  }

  if (opcoes) {
    const alimentador = (ALIMENTADOR.exec(texto) ?? ALIMENTADOR.exec(textoResposta))?.[0].toUpperCase()
    const atendidos = opcoes.alimentadores.find((item) => item.codigo === alimentador)?.municipios

    const nomesMunicipios = opcoes.municipios.map(({ nome }) => nome)
    let municipio =
      maisLongoMencionado(texto, nomesMunicipios) ?? primeiroMencionado(textoResposta, nomesMunicipios)
    // O município fica só se o alimentador citado o atende
    if (atendidos && municipio && !atendidos.includes(municipio)) {
      municipio = undefined
    }
    aplicar('municipio', municipio)

    // O bairro só vale dentro do município (há "Centro" em vários) e quando
    // não é o próprio nome do município
    const bairros = opcoes.municipios.find(({ nome }) => nome === municipio)?.bairros ?? []
    aplicar(
      'bairro',
      maisLongoMencionado(
        texto,
        bairros.filter((bairro) => normalizar(bairro) !== normalizar(municipio ?? '')),
      ),
    )

    const classe = opcoes.classes.find((codigo) => sinaisClasse[codigo]?.test(texto))
    aplicar('classe', classe, classe && classesConsumo[classe].label)

    aplicar('alimentador', atendidos ? alimentador : undefined)

    const causa = opcoes.causas.find((codigo) => menciona(texto, codigo) || menciona(texto, rotuloCausa(codigo)))
    aplicar('causa', causa, causa && rotuloCausa(causa))
  }

  const busca = params.toString()
  return { caminho: busca ? `${tela.to}?${busca}` : tela.to, filtros }
}
