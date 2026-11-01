import AvisoSazonalidade from '@/components/AvisoSazonalidade/AvisoSazonalidade'
import BlocoDados from '@/components/BlocoDados/BlocoDados'
import CabecalhoPagina from '@/components/CabecalhoPagina/CabecalhoPagina'
import CartaoKpi from '@/components/CartaoKpi/CartaoKpi'
import CartaoKpiEsqueleto from '@/components/CartaoKpi/CartaoKpiEsqueleto'
import EstadoConsulta from '@/components/EstadoConsulta/EstadoConsulta'
import FiltrosGlobais from '@/components/FiltrosGlobais/FiltrosGlobais'
import GraficosMensais from '@/components/GraficosMensais/GraficosMensais'
import Nota from '@/components/Nota/Nota'
import OcorrenciasPorCausa from '@/components/OcorrenciasPorCausa/OcorrenciasPorCausa'
import RankingAlimentadores from '@/components/RankingAlimentadores/RankingAlimentadores'
import { rotuloCausa } from '@/config/causas'
import { alimentadorEmDestaque, useContinuidade, type ContinuidadeRede } from '@/hooks/use-continuidade'
import { useFiltros } from '@/hooks/use-filtros'
import { variacaoPercentual } from '@/lib/comparacao'
import { formatarNumero, formatarPeriodo } from '@/lib/formatacao'

const semAlimentadores = (dados: ContinuidadeRede) => dados.ranking.length === 0
const MENSAGEM_VAZIO = 'Nenhum alimentador para esses filtros.'

const horas = (valor: number) => `${formatarNumero(valor)} h`

function Kpis({ dados, causa }: { dados: ContinuidadeRede; causa?: string }) {
  const { periodo, periodo_anterior, ranking, ocorrencias } = dados
  const pior = alimentadorEmDestaque(ranking)
  // Os alimentadores pequenos com DEC maior ficaram de fora do destaque
  const semPequenos = pior !== ranking[0]
  const pequenos = ranking.filter((linha) => linha.alimentador_pequeno).length
  const principal = ocorrencias.por_causa[0]

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        <span className="font-semibold text-foreground">{formatarPeriodo(periodo.inicio, periodo.fim)}</span>, comparado
        com {formatarPeriodo(periodo_anterior.inicio, periodo_anterior.fim)}
      </p>
      <AvisoSazonalidade base={periodo_anterior} comparado={periodo} />
      <Nota titulo="Como ler DEC e FEC">
        São sempre do alimentador inteiro, inclusive das UCs de outros municípios. O município só escolhe quais
        alimentadores aparecem, e a causa filtra só as ocorrências.
      </Nota>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <CartaoKpi
          titulo="Alimentadores no recorte"
          valor={formatarNumero(ranking.length)}
          detalhe={pequenos > 0 ? `${formatarNumero(pequenos)} com menos de 100 UCs` : undefined}
        />
        <CartaoKpi
          titulo={semPequenos ? 'Pior DEC (100 UCs ou mais)' : 'Pior DEC'}
          valor={horas(pior.dec)}
          detalhe={`${pior.alimentador} · ${pior.municipio_principal}`}
        />
        <CartaoKpi
          titulo="Ocorrências no período"
          valor={formatarNumero(ocorrencias.total)}
          variacao={variacaoPercentual(ocorrencias.total, ocorrencias.total_anterior)}
          sentido="subir-e-ruim"
          complementoVariacao="vs. período anterior"
          detalhe={causa ? `Só ${rotuloCausa(causa).toLowerCase()}` : 'UCs interrompidas'}
        />
        <CartaoKpi
          titulo="Principal causa"
          valor={principal ? rotuloCausa(principal.causa) : '—'}
          detalhe={
            principal && ocorrencias.total > 0
              ? `${formatarNumero((principal.ocorrencias / ocorrencias.total) * 100)}% das ocorrências`
              : undefined
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

function ContinuidadePage() {
  const { filtros, alterarFiltro } = useFiltros()
  const consulta = useContinuidade(filtros)
  // A série que vem na resposta é a do primeiro do ranking. Sem alimentador escolhido, se ele for
  // pequeno, o gráfico busca a série do alimentador em destaque numa consulta só para ele
  const destaque = consulta.data && !filtros.alimentador ? alimentadorEmDestaque(consulta.data.ranking) : undefined
  const outraSerie = destaque !== undefined && consulta.data?.serie?.alimentador !== destaque.alimentador
  const consultaSerie = useContinuidade(
    { ...filtros, alimentador: destaque?.alimentador },
    // Enquanto um filtro novo carrega, o destaque ainda é o dos números antigos
    outraSerie && !consulta.isPlaceholderData,
  )
  // Com uma causa só (ou nenhuma), o bloco das causas repetiria o cartão "Principal causa"
  // numa caixa quase vazia: ele sai e o gráfico ocupa a largura toda
  const variasCausas = (consulta.data?.ocorrencias.por_causa.length ?? 2) > 1

  return (
    <section className="flex flex-col gap-6">
      <CabecalhoPagina acoes={<FiltrosGlobais campos={['comparacao', 'municipio', 'alimentador', 'causa']} />} />

      <EstadoConsulta
        consulta={consulta}
        estaVazio={semAlimentadores}
        mensagemVazio={MENSAGEM_VAZIO}
        esqueleto={<KpisEsqueleto />}
      >
        {(dados) => <Kpis dados={dados} causa={filtros.causa} />}
      </EstadoConsulta>

      <div className="grid gap-4 xl:grid-cols-5">
        <BlocoDados
          className={variasCausas ? 'xl:col-span-3' : 'xl:col-span-5'}
          titulo="DEC e FEC por mês"
          descricao="Do alimentador escolhido ou, sem escolha, do pior DEC entre os com 100 UCs ou mais"
          consulta={outraSerie ? consultaSerie : consulta}
          estaVazio={(dados) => dados.serie === null}
          mensagemVazio={MENSAGEM_VAZIO}
        >
          {(dados) =>
            dados.serie && (
              <div className="flex flex-col gap-3">
                <p className="tabular-nums text-[13px] font-semibold">{dados.serie.alimentador}</p>
                <GraficosMensais
                  atual={dados.serie.atual}
                  anterior={dados.serie.anterior}
                  medidas={[
                    { chave: 'dec', titulo: 'DEC (horas sem energia por UC)', formatar: horas, sentido: 'subir-e-ruim' },
                    {
                      chave: 'fec',
                      titulo: 'FEC (interrupções por UC)',
                      formatar: formatarNumero,
                      sentido: 'subir-e-ruim',
                    },
                  ]}
                  sincronia="continuidade-por-mes"
                />
              </div>
            )
          }
        </BlocoDados>
        {variasCausas && (
          <BlocoDados
            className="xl:col-span-2"
            titulo="Ocorrências por causa"
            descricao="UCs interrompidas no período, nos alimentadores do recorte"
            consulta={consulta}
            estaVazio={(dados) => dados.ocorrencias.total === 0}
            mensagemVazio="Nenhuma ocorrência para esses filtros."
          >
            {(dados) => <OcorrenciasPorCausa porCausa={dados.ocorrencias.por_causa} />}
          </BlocoDados>
        )}
      </div>

      <BlocoDados
        titulo="Piores alimentadores"
        descricao="Do maior DEC para o menor: onde a manutenção preventiva rende mais. Clique no código para filtrar."
        consulta={consulta}
        estaVazio={semAlimentadores}
        mensagemVazio={MENSAGEM_VAZIO}
      >
        {(dados) => (
          <RankingAlimentadores
            ranking={dados.ranking}
            escolhido={filtros.alimentador}
            aoEscolher={(alimentador) => alterarFiltro('alimentador', alimentador)}
            aoVerTodos={() => alterarFiltro('alimentador')}
          />
        )}
      </BlocoDados>
    </section>
  )
}

export default ContinuidadePage
