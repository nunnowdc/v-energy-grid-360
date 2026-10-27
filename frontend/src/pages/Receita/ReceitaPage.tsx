import BlocoDados from '@/components/BlocoDados/BlocoDados'
import CabecalhoPagina from '@/components/CabecalhoPagina/CabecalhoPagina'
import CartaoKpi from '@/components/CartaoKpi/CartaoKpi'
import CartaoKpiEsqueleto from '@/components/CartaoKpi/CartaoKpiEsqueleto'
import DetalheReceita, { type PassoTrilha } from '@/components/DetalheReceita/DetalheReceita'
import EstadoConsulta from '@/components/EstadoConsulta/EstadoConsulta'
import FiltrosGlobais from '@/components/FiltrosGlobais/FiltrosGlobais'
import PonteReceita from '@/components/PonteReceita/PonteReceita'
import Variacao from '@/components/Variacao/Variacao'
import { useFiltros } from '@/hooks/use-filtros'
import { useReceita, type VariacaoReceita } from '@/hooks/use-receita'
import { variacaoPercentual } from '@/lib/comparacao'
import {
  formatarMoeda,
  formatarMoedaCompacta,
  formatarMoedaCompactaComSinal,
  formatarNumero,
  formatarPercentualComSinal,
  formatarPeriodo,
} from '@/lib/formatacao'

const semReceita = (dados: VariacaoReceita) => dados.total.receita_p0 === 0 && dados.total.receita_p1 === 0
const MENSAGEM_VAZIO = 'Nenhuma receita para esses filtros.'

const precoPorKwh = (preco: number | null) => (preco === null ? '—' : `${formatarMoeda(preco)}/kWh`)

function Kpis({ dados }: { dados: VariacaoReceita }) {
  const { total, periodo_p0, periodo_p1 } = dados
  const variacaoConsumo = variacaoPercentual(total.kwh_p1, total.kwh_p0)

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        Período base <span className="font-semibold text-foreground">{formatarPeriodo(periodo_p0.inicio, periodo_p0.fim)}</span>{' '}
        × período comparado{' '}
        <span className="font-semibold text-foreground">{formatarPeriodo(periodo_p1.inicio, periodo_p1.fim)}</span>
        <span> · períodos fixos da base</span>
      </p>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <CartaoKpi titulo="Receita no período base" valor={formatarMoedaCompacta(total.receita_p0)} />
        <CartaoKpi
          titulo="Receita no período comparado"
          valor={formatarMoedaCompacta(total.receita_p1)}
          variacao={variacaoPercentual(total.receita_p1, total.receita_p0)}
          complementoVariacao="vs. período base"
        />
        <CartaoKpi
          titulo="Efeito preço"
          valor={formatarMoedaCompactaComSinal(total.efeito_preco)}
          detalhe={`Preço médio ${precoPorKwh(total.preco_p0)} → ${precoPorKwh(total.preco_p1)}`}
        />
        <CartaoKpi
          titulo="Efeito volume"
          valor={formatarMoedaCompactaComSinal(total.efeito_volume)}
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

// Quanto do efeito volume vem das UCs com geração própria, quando os dois
// apontam para o mesmo lado (senão o percentual não faz sentido)
function parteDaGd({ total, por_gd }: VariacaoReceita) {
  const comGd = por_gd.find((grupo) => grupo.possui_gd)
  if (!comGd || total.efeito_volume === 0) {
    return undefined
  }
  const parte = (comGd.efeito_volume / total.efeito_volume) * 100
  return parte >= 0 && parte <= 100 ? parte : undefined
}

function GeracaoPropria({ dados }: { dados: VariacaoReceita }) {
  const parte = parteDaGd(dados)
  // Com geração própria primeiro
  const grupos = [...dados.por_gd].sort((a, b) => Number(b.possui_gd) - Number(a.possui_gd))

  return (
    <div className="flex flex-col gap-4">
      {parte !== undefined && (
        <p className="text-sm">
          <span className="font-mono font-semibold">{formatarNumero(parte)}%</span> do efeito volume vem das UCs com
          geração própria.
        </p>
      )}
      <dl className="flex flex-col gap-3">
        {grupos.map((grupo) => {
          const variacaoConsumo = variacaoPercentual(grupo.kwh_p1, grupo.kwh_p0)
          return (
            <div key={String(grupo.possui_gd)} className="flex flex-col gap-2 rounded-md border p-3">
              <dt className="text-[13px] font-semibold">
                {grupo.possui_gd ? 'Com geração própria' : 'Sem geração própria'}
                <span className="font-normal text-muted-foreground">
                  {' '}
                  · {formatarNumero(grupo.ucs_p1)} UCs
                </span>
              </dt>
              <dd className="grid grid-cols-3 gap-2 text-xs">
                <div className="flex flex-col gap-0.5">
                  <span className="text-muted-foreground">Consumo medido</span>
                  {variacaoConsumo === undefined ? '—' : <Variacao percentual={variacaoConsumo} />}
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-muted-foreground">Efeito volume</span>
                  <span className="font-mono text-[13px] whitespace-nowrap">{formatarMoedaCompactaComSinal(grupo.efeito_volume)}</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-muted-foreground">Efeito preço</span>
                  <span className="font-mono text-[13px] whitespace-nowrap">{formatarMoedaCompactaComSinal(grupo.efeito_preco)}</span>
                </div>
              </dd>
            </div>
          )
        })}
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
      <CabecalhoPagina acoes={<FiltrosGlobais campos={['municipio', 'bairro', 'classe']} />} />

      <EstadoConsulta
        consulta={consulta}
        estaVazio={semReceita}
        mensagemVazio={MENSAGEM_VAZIO}
        esqueleto={<KpisEsqueleto />}
      >
        {(dados) => <Kpis dados={dados} />}
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
          {(dados) => <PonteReceita total={dados.total} />}
        </BlocoDados>
        <BlocoDados
          className="xl:col-span-2"
          titulo="Com e sem geração própria"
          descricao="UCs com painel solar medem menos consumo da distribuidora"
          consulta={consulta}
          estaVazio={semReceita}
          mensagemVazio={MENSAGEM_VAZIO}
        >
          {(dados) => <GeracaoPropria dados={dados} />}
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
