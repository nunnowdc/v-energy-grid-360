import { Lightbulb } from 'lucide-react'
import AvisoSazonalidade from '@/components/AvisoSazonalidade/AvisoSazonalidade'
import BlocoDados from '@/components/BlocoDados/BlocoDados'
import CabecalhoPagina from '@/components/CabecalhoPagina/CabecalhoPagina'
import CartaoKpi from '@/components/CartaoKpi/CartaoKpi'
import CartaoKpiEsqueleto from '@/components/CartaoKpi/CartaoKpiEsqueleto'
import DetalheReceita, { type PassoTrilha } from '@/components/DetalheReceita/DetalheReceita'
import EstadoConsulta from '@/components/EstadoConsulta/EstadoConsulta'
import FiltrosGlobais from '@/components/FiltrosGlobais/FiltrosGlobais'
import PonteReceita from '@/components/PonteReceita/PonteReceita'
import ValorEfeito from '@/components/ValorEfeito/ValorEfeito'
import Variacao from '@/components/Variacao/Variacao'
import { useFiltros } from '@/hooks/use-filtros'
import { temDados, useReceita, type DecomposicaoCompleta, type VariacaoReceita } from '@/hooks/use-receita'
import { tomDaVariacao, variacaoPercentual } from '@/lib/comparacao'
import {
  formatarMoeda,
  formatarMoedaCompacta,
  formatarMoedaCompactaComSinal,
  formatarNumero,
  formatarPercentualComSinal,
  formatarPeriodo,
} from '@/lib/formatacao'

// Recorte sem nenhuma linha na Gold (ex.: bairro sem UC da classe escolhida)
const semReceita = (dados: VariacaoReceita) => !temDados(dados.total)
const MENSAGEM_VAZIO = 'Nenhuma receita para esses filtros.'

const precoPorKwh = (preco: number | null) => (preco === null ? '—' : `${formatarMoeda(preco)}/kWh`)

function Kpis({ dados, total }: { dados: VariacaoReceita; total: DecomposicaoCompleta }) {
  const { periodo_p0, periodo_p1 } = dados
  const variacaoConsumo = variacaoPercentual(total.kwh_p1, total.kwh_p0)

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        Período base <span className="font-semibold text-foreground">{formatarPeriodo(periodo_p0.inicio, periodo_p0.fim)}</span>{' '}
        × período comparado{' '}
        <span className="font-semibold text-foreground">{formatarPeriodo(periodo_p1.inicio, periodo_p1.fim)}</span>
      </p>
      <AvisoSazonalidade base={periodo_p0} comparado={periodo_p1} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <CartaoKpi titulo="Receita no período base" valor={formatarMoedaCompacta(total.receita_p0)} />
        <CartaoKpi
          titulo="Receita no período comparado"
          valor={formatarMoedaCompacta(total.receita_p1)}
          variacao={variacaoPercentual(total.receita_p1, total.receita_p0)}
          sentido="subir-e-bom"
          complementoVariacao="vs. período base"
        />
        <CartaoKpi
          titulo="Efeito preço"
          valor={formatarMoedaCompactaComSinal(total.efeito_preco)}
          tomValor={tomDaVariacao(total.efeito_preco, 'subir-e-bom')}
          detalhe={`Preço médio ${precoPorKwh(total.preco_p0)} → ${precoPorKwh(total.preco_p1)}`}
        />
        <CartaoKpi
          titulo="Efeito volume"
          valor={formatarMoedaCompactaComSinal(total.efeito_volume)}
          tomValor={tomDaVariacao(total.efeito_volume, 'subir-e-bom')}
          detalhe={
            variacaoConsumo === undefined
              ? undefined
              : `Consumo medido ${formatarPercentualComSinal(variacaoConsumo)}`
          }
        />
      </div>
    </div>
  )
}

function KpisEsqueleto() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: 4 }, (_, indice) => (
        <CartaoKpiEsqueleto key={indice} />
      ))}
    </div>
  )
}

type Grupo = VariacaoReceita['por_gd'][number]

// Frase sobre quem puxou o efeito volume, quando os dois grupos têm dados
function fraseDoVolume(total: DecomposicaoCompleta, comGd?: Grupo, semGd?: Grupo) {
  if (!comGd || !semGd || !temDados(comGd) || !temDados(semGd) || total.efeito_volume === 0) {
    return undefined
  }
  // A queda vem só das UCs com geração própria: nas demais, o volume cresceu
  if (total.efeito_volume < 0 && comGd.efeito_volume < 0 && semGd.efeito_volume >= 0) {
    return (
      <>
        A queda de volume vem das UCs com geração própria (<ValorEfeito reais={comGd.efeito_volume} />). Nas
        demais, o volume cresceu (<ValorEfeito reais={semGd.efeito_volume} />).
      </>
    )
  }
  const parte = (comGd.efeito_volume / total.efeito_volume) * 100
  return parte >= 0 && parte <= 100
    ? `${formatarNumero(parte)}% do efeito volume vem das UCs com geração própria.`
    : undefined
}

function Grupo({ grupo }: { grupo: Grupo }) {
  const nome = grupo.possui_gd ? 'Com geração própria' : 'Sem geração própria'

  if (!temDados(grupo)) {
    return (
      <div className="flex flex-col gap-1 rounded-md border border-dashed bg-card p-3">
        <dt className="text-[13px] font-semibold">{nome}</dt>
        <dd className="text-xs text-muted-foreground">Nenhuma UC neste recorte.</dd>
      </div>
    )
  }

  const variacaoConsumo = variacaoPercentual(grupo.kwh_p1, grupo.kwh_p0)
  return (
    <div className="flex flex-col gap-2 rounded-md border bg-card p-3">
      <dt className="text-[13px] font-semibold">
        {nome}
        <span className="font-normal text-muted-foreground">
          {' '}
          · {formatarNumero(grupo.ucs_p1)} {grupo.ucs_p1 === 1 ? 'UC' : 'UCs'}
        </span>
      </dt>
      <dd className="grid grid-cols-3 gap-2 text-xs">
        <div className="flex flex-col gap-0.5">
          <span className="text-muted-foreground">Consumo medido</span>
          {variacaoConsumo === undefined ? '—' : <Variacao percentual={variacaoConsumo} sentido="subir-e-bom" />}
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-muted-foreground">Efeito volume</span>
          <span className="text-[13px]"><ValorEfeito reais={grupo.efeito_volume} /></span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-muted-foreground">Efeito preço</span>
          <span className="text-[13px]"><ValorEfeito reais={grupo.efeito_preco} /></span>
        </div>
      </dd>
    </div>
  )
}

function GeracaoPropria({ dados, total }: { dados: VariacaoReceita; total: DecomposicaoCompleta }) {
  const comGd = dados.por_gd.find((grupo) => grupo.possui_gd)
  const semGd = dados.por_gd.find((grupo) => !grupo.possui_gd)
  const frase = fraseDoVolume(total, comGd, semGd)

  return (
    <div className="flex flex-col gap-4">
      {frase && <p className="text-[15px] leading-relaxed font-medium">{frase}</p>}
      <dl className="flex flex-col gap-3">
        {[comGd, semGd].map((grupo) => grupo && <Grupo key={String(grupo.possui_gd)} grupo={grupo} />)}
      </dl>
    </div>
  )
}

function ReceitaPage() {
  const { filtros, alterarFiltro } = useFiltros()
  const consulta = useReceita(filtros)
  const { municipio, bairro, classe } = filtros

  const trilha: PassoTrilha[] = [
    { rotulo: 'Todos os municípios', aoClicar: municipio ? () => alterarFiltro('municipio') : undefined },
    ...(municipio ? [{ rotulo: municipio, aoClicar: bairro ? () => alterarFiltro('bairro') : undefined }] : []),
    ...(bairro ? [{ rotulo: bairro }] : []),
  ]

  function aoDescer(nome: string) {
    if (!municipio) {
      alterarFiltro('municipio', nome)
    } else if (!bairro) {
      alterarFiltro('bairro', nome)
    } else {
      alterarFiltro('classe', nome)
    }
  }

  // Num bairro com a classe escolhida, não há mais para onde descer
  const podeDescer = !(bairro && classe)

  return (
    <section className="flex flex-col gap-6">
      <CabecalhoPagina acoes={<FiltrosGlobais campos={['comparacao', 'municipio', 'bairro', 'classe']} padraoComparacao="inicio-da-base" />} />

      <EstadoConsulta
        consulta={consulta}
        estaVazio={semReceita}
        mensagemVazio={MENSAGEM_VAZIO}
        esqueleto={<KpisEsqueleto />}
      >
        {(dados) => temDados(dados.total) && <Kpis dados={dados} total={dados.total} />}
      </EstadoConsulta>

      <div className="grid gap-4 xl:grid-cols-5">
        <BlocoDados
          className="xl:col-span-3"
          titulo="Ponte da receita"
          descricao="Efeito volume = variação do consumo × preço base. Efeito preço = variação do preço × consumo comparado."
          consulta={consulta}
          estaVazio={semReceita}
          mensagemVazio={MENSAGEM_VAZIO}
        >
          {(dados) => temDados(dados.total) && <PonteReceita total={dados.total} />}
        </BlocoDados>
        {/* Bloco de destaque: fundo petróleo claro para se diferenciar dos blocos comuns.
            Não usa o visual dos insights de IA, que é outro */}
        <BlocoDados
          className="bg-primary/5 ring-primary/25 xl:col-span-2"
          acao={
            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
              <Lightbulb aria-hidden="true" className="size-3.5" />
              Destaque
            </span>
          }
          titulo="Com e sem geração própria"
          descricao="UCs com painel solar medem menos consumo da distribuidora"
          consulta={consulta}
          estaVazio={semReceita}
          mensagemVazio={MENSAGEM_VAZIO}
        >
          {(dados) => temDados(dados.total) && <GeracaoPropria dados={dados} total={dados.total} />}
        </BlocoDados>
      </div>

      <BlocoDados
        titulo="Onde está a variação"
        descricao="Da maior perda de volume para a menor. Clique numa linha para detalhar."
        consulta={consulta}
        estaVazio={semReceita}
        mensagemVazio={MENSAGEM_VAZIO}
      >
        {(dados) => (
          <DetalheReceita
            detalhamento={dados.detalhamento}
            trilha={trilha}
            aoDescer={podeDescer ? aoDescer : undefined}
          />
        )}
      </BlocoDados>
    </section>
  )
}

export default ReceitaPage
