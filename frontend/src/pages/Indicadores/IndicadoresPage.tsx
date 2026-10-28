import BlocoDados from '@/components/BlocoDados/BlocoDados'
import CabecalhoPagina from '@/components/CabecalhoPagina/CabecalhoPagina'
import CartaoKpi from '@/components/CartaoKpi/CartaoKpi'
import CartaoKpiEsqueleto from '@/components/CartaoKpi/CartaoKpiEsqueleto'
import EstadoConsulta from '@/components/EstadoConsulta/EstadoConsulta'
import FiltrosGlobais from '@/components/FiltrosGlobais/FiltrosGlobais'
import GraficosMensais from '@/components/GraficosMensais/GraficosMensais'
import ReceitaPorClasse from '@/components/ReceitaPorClasse/ReceitaPorClasse'
import { useFiltros } from '@/hooks/use-filtros'
import { useIndicadores, type IndicadoresGerais } from '@/hooks/use-indicadores'
import { variacaoPercentual } from '@/lib/comparacao'
import {
  formatarCompetencia,
  formatarEnergia,
  formatarMoeda,
  formatarMoedaCompacta,
  formatarNumero,
  formatarPeriodo,
} from '@/lib/formatacao'

const COMPLEMENTO = 'vs. período anterior'

const semFaturas = (dados: IndicadoresGerais) => dados.atual.faturas === 0

function Kpis({ dados }: { dados: IndicadoresGerais }) {
  const { atual, anterior, mensal } = dados
  const percentualAtraso = atual.faturas > 0 ? (atual.faturas_atrasadas / atual.faturas) * 100 : 0

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        <span className="font-semibold text-foreground">{formatarPeriodo(atual.inicio, atual.fim)}</span>, comparado
        com {formatarPeriodo(anterior.inicio, anterior.fim)}
      </p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        <CartaoKpi
          titulo="Receita faturada"
          valor={formatarMoedaCompacta(atual.receita_faturada)}
          variacao={variacaoPercentual(atual.receita_faturada, anterior.receita_faturada)}
          complementoVariacao={COMPLEMENTO}
          tendencia={mensal.atual.map((mes) => mes.receita_faturada)}
        />
        <CartaoKpi
          titulo="Consumo medido"
          valor={formatarEnergia(atual.consumo_kwh)}
          variacao={variacaoPercentual(atual.consumo_kwh, anterior.consumo_kwh)}
          complementoVariacao={COMPLEMENTO}
          tendencia={mensal.atual.map((mes) => mes.consumo_kwh)}
        />
        <CartaoKpi
          titulo="Preço médio"
          valor={atual.preco_medio_kwh === null ? '—' : `${formatarMoeda(atual.preco_medio_kwh)}/kWh`}
          variacao={
            atual.preco_medio_kwh !== null && anterior.preco_medio_kwh !== null
              ? variacaoPercentual(atual.preco_medio_kwh, anterior.preco_medio_kwh)
              : undefined
          }
          complementoVariacao={COMPLEMENTO}
          detalhe="Receita ÷ consumo medido"
        />
        <CartaoKpi
          titulo="UCs faturadas"
          valor={formatarNumero(atual.ucs_faturadas)}
          variacao={variacaoPercentual(atual.ucs_faturadas, anterior.ucs_faturadas)}
          complementoVariacao={`vs. ${formatarCompetencia(anterior.fim)}`}
          detalhe={`Em ${formatarCompetencia(atual.fim)}`}
        />
        <CartaoKpi
          titulo="Faturas em atraso"
          valor={formatarNumero(atual.faturas_atrasadas)}
          variacao={variacaoPercentual(atual.faturas_atrasadas, anterior.faturas_atrasadas)}
          complementoVariacao={COMPLEMENTO}
          detalhe={`${formatarNumero(percentualAtraso)}% das faturas do período`}
        />
      </div>
    </div>
  )
}

function KpisEsqueleto() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
      {Array.from({ length: 5 }, (_, indice) => (
        <CartaoKpiEsqueleto key={indice} />
      ))}
    </div>
  )
}

function IndicadoresPage() {
  const { filtros } = useFiltros()
  const consulta = useIndicadores(filtros)
  const mensagemVazio = 'Nenhuma fatura para esses filtros.'

  return (
    <section className="flex flex-col gap-6">
      <CabecalhoPagina acoes={<FiltrosGlobais campos={['periodo', 'ate', 'municipio', 'classe']} />} />

      <EstadoConsulta
        consulta={consulta}
        estaVazio={semFaturas}
        mensagemVazio={mensagemVazio}
        esqueleto={<KpisEsqueleto />}
      >
        {(dados) => <Kpis dados={dados} />}
      </EstadoConsulta>

      <div className="grid gap-4 lg:grid-cols-3">
        <BlocoDados
          className="lg:col-span-2"
          titulo="Receita e consumo por mês"
          descricao="Cada mês ao lado do mês na mesma posição do período anterior"
          consulta={consulta}
          estaVazio={semFaturas}
          mensagemVazio={mensagemVazio}
        >
          {(dados) => (
            <GraficosMensais
              atual={dados.mensal.atual}
              anterior={dados.mensal.anterior}
              medidas={[
                { chave: 'receita_faturada', titulo: 'Receita faturada (R$)', formatar: formatarMoedaCompacta },
                { chave: 'consumo_kwh', titulo: 'Consumo medido (kWh)', formatar: formatarEnergia },
              ]}
              sincronia="indicadores-por-mes"
            />
          )}
        </BlocoDados>
        <BlocoDados
          titulo="Receita por classe de consumo"
          descricao="Receita faturada no período escolhido"
          consulta={consulta}
          estaVazio={semFaturas}
          mensagemVazio={mensagemVazio}
        >
          {(dados) => <ReceitaPorClasse classes={dados.por_classe} />}
        </BlocoDados>
      </div>
    </section>
  )
}

export default IndicadoresPage
