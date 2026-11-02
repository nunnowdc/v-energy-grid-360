import { useSearchParams } from 'react-router'
import BlocoDados from '@/components/BlocoDados/BlocoDados'
import CabecalhoPagina from '@/components/CabecalhoPagina/CabecalhoPagina'
import CartaoKpi from '@/components/CartaoKpi/CartaoKpi'
import CartaoKpiEsqueleto from '@/components/CartaoKpi/CartaoKpiEsqueleto'
import EstadoConsulta from '@/components/EstadoConsulta/EstadoConsulta'
import JanelaDias from '@/components/JanelaDias/JanelaDias'
import Nota from '@/components/Nota/Nota'
import PerguntasPorDia from '@/components/PerguntasPorDia/PerguntasPorDia'
import TempoTokensPorDia from '@/components/TempoTokensPorDia/TempoTokensPorDia'
import UltimasPerguntas from '@/components/UltimasPerguntas/UltimasPerguntas'
import { janelasDias, useUsoAgente, type JanelaDias as Janela, type UsoAgente } from '@/hooks/use-uso-agente'
import { formatarData, formatarNumero, formatarNumeroCompacto, formatarSegundos } from '@/lib/formatacao'

const JANELA_PADRAO: Janela = 30

// ?dias=7|30|90 no endereço; qualquer outro valor vale o padrão
function lerJanela(params: URLSearchParams): Janela {
  const dias = Number(params.get('dias'))
  return janelasDias.find((janela) => janela === dias) ?? JANELA_PADRAO
}

const semPerguntas = (dados: UsoAgente) => dados.resumo.perguntas === 0

// Parte do total, ex.: 74 de 97 → "76,3%"
function percentual(parte: number, total: number) {
  return total > 0 ? `${formatarNumero((parte / total) * 100)}%` : '—'
}

function Kpis({ dados }: { dados: UsoAgente }) {
  const { resumo, por_dia: dias, inicio, fim } = dados
  const respondidas = resumo.respondidas_com_dados + resumo.respondidas_com_documentos
  const avaliacoes = resumo.avaliacoes_uteis + resumo.avaliacoes_inuteis

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        De <span className="font-semibold text-foreground">{formatarData(inicio)}</span> a{' '}
        <span className="font-semibold text-foreground">{formatarData(fim)}</span> (hoje)
      </p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">
        <CartaoKpi
          titulo="Perguntas"
          valor={formatarNumero(resumo.perguntas)}
          detalhe={`Média de ${formatarNumero(resumo.perguntas / dias.length)} por dia`}
          tendencia={dias.map((dia) => dia.perguntas)}
        />
        <CartaoKpi
          titulo="Respondidas"
          valor={percentual(respondidas, resumo.perguntas)}
          detalhe={`${formatarNumero(resumo.respondidas_com_dados)} com dados e ${formatarNumero(resumo.respondidas_com_documentos)} com documentos`}
        />
        <CartaoKpi
          titulo="Sem resposta segura"
          valor={percentual(resumo.recusas, resumo.perguntas)}
          detalhe={`${formatarNumero(resumo.recusas)} recusas e ${formatarNumero(resumo.erros)} erros`}
        />
        <CartaoKpi
          titulo="Tempo médio de resposta"
          valor={resumo.tempo_medio_ms === null ? '—' : formatarSegundos(resumo.tempo_medio_ms)}
          detalhe={resumo.tempo_p95_ms === null ? undefined : `95% em até ${formatarSegundos(resumo.tempo_p95_ms)}`}
        />
        <CartaoKpi
          titulo="Tokens por pergunta"
          valor={resumo.tokens_medio === null ? '—' : formatarNumero(Math.round(resumo.tokens_medio))}
          detalhe={`${formatarNumeroCompacto(resumo.tokens_total)} no período`}
        />
        <CartaoKpi
          titulo="Avaliações"
          valor={formatarNumero(avaliacoes)}
          detalhe={`${formatarNumero(resumo.avaliacoes_uteis)} úteis e ${formatarNumero(resumo.avaliacoes_inuteis)} não úteis`}
        />
      </div>
    </div>
  )
}

function KpisEsqueleto() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">
      {Array.from({ length: 6 }, (_, indice) => (
        <CartaoKpiEsqueleto key={indice} />
      ))}
    </div>
  )
}

function AgenteIaPage() {
  const [params, setParams] = useSearchParams()
  const janela = lerJanela(params)
  const consulta = useUsoAgente(janela)
  const mensagemVazio = 'Nenhuma pergunta ao agente nesse período.'

  // replace: trocar a janela não cria uma entrada nova no "Voltar" do navegador
  function mudarJanela(dias: Janela) {
    setParams(
      (atual) => {
        const novos = new URLSearchParams(atual)
        if (dias === JANELA_PADRAO) {
          novos.delete('dias')
        } else {
          novos.set('dias', String(dias))
        }
        return novos
      },
      { replace: true },
    )
  }

  return (
    <section className="flex flex-col gap-6">
      <CabecalhoPagina acoes={<JanelaDias valor={janela} aoMudar={mudarJanela} />} />

      <Nota titulo="De onde vêm os números">
        Cada pergunta feita ao agente no portal fica gravada na auditoria, com o resultado, o tempo e os tokens
        gastos. As perguntas de antes do login não têm perfil.
      </Nota>

      <EstadoConsulta
        consulta={consulta}
        estaVazio={semPerguntas}
        mensagemVazio={mensagemVazio}
        esqueleto={<KpisEsqueleto />}
      >
        {(dados) => <Kpis dados={dados} />}
      </EstadoConsulta>

      <div className="grid gap-4 lg:grid-cols-2">
        <BlocoDados
          titulo="Perguntas por dia"
          descricao="Separadas pelo resultado de cada resposta"
          consulta={consulta}
          estaVazio={semPerguntas}
          mensagemVazio={mensagemVazio}
        >
          {(dados) => <PerguntasPorDia dias={dados.por_dia} />}
        </BlocoDados>
        <BlocoDados
          titulo="Tempo e tokens por dia"
          descricao="Média das perguntas de cada dia"
          consulta={consulta}
          estaVazio={semPerguntas}
          mensagemVazio={mensagemVazio}
        >
          {(dados) => <TempoTokensPorDia dias={dados.por_dia} />}
        </BlocoDados>
      </div>

      <BlocoDados
        titulo="Últimas perguntas"
        descricao="As 20 mais recentes do período, com o passo a passo de cada resposta"
        consulta={consulta}
        estaVazio={semPerguntas}
        mensagemVazio={mensagemVazio}
      >
        {(dados) => <UltimasPerguntas perguntas={dados.ultimas} />}
      </BlocoDados>
    </section>
  )
}

export default AgenteIaPage
