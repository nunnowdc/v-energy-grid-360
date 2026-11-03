import BlocoDados from '@/components/BlocoDados/BlocoDados'
import CabecalhoPagina from '@/components/CabecalhoPagina/CabecalhoPagina'
import CartaoKpi from '@/components/CartaoKpi/CartaoKpi'
import CartaoKpiEsqueleto from '@/components/CartaoKpi/CartaoKpiEsqueleto'
import CasosAvaliacao from '@/components/CasosAvaliacao/CasosAvaliacao'
import EstadoConsulta from '@/components/EstadoConsulta/EstadoConsulta'
import EvolucaoAvaliacoes from '@/components/EvolucaoAvaliacoes/EvolucaoAvaliacoes'
import Nota from '@/components/Nota/Nota'
import { atingiuMeta, metasAvaliacao, type MetaAvaliacao } from '@/config/metas-avaliacao'
import { useAvaliacoesAgente, type AvaliacoesAgente, type ExecucaoAvaliacao } from '@/hooks/use-avaliacoes-agente'
import { formatarInstante, formatarNumero } from '@/lib/formatacao'

const COMANDO = 'python -m scripts.avaliar_golden_set'

const semExecucoes = (dados: AvaliacoesAgente) => dados.execucoes.length === 0

function CartaoMeta({ meta, execucao }: { meta: MetaAvaliacao; execucao: ExecucaoAvaliacao }) {
  const valor = execucao[meta.chave]
  const atingiu = atingiuMeta(meta, execucao)

  if (valor === null) {
    return <CartaoKpi titulo={meta.titulo} valor="—" detalhe="Sem casos desse tipo nesta execução" />
  }
  return (
    <CartaoKpi
      titulo={meta.titulo}
      valor={meta.sentido === 'maximo' ? formatarNumero(Math.round(valor)) : `${formatarNumero(valor)}%`}
      tomValor={atingiu ? 'positivo' : 'negativo'}
      detalhe={`Meta: ${meta.textoMeta} · ${atingiu ? 'atingida' : 'não atingida'}`}
    />
  )
}

function UltimaExecucao({ dados }: { dados: AvaliacoesAgente }) {
  const ultima = dados.execucoes.at(-1)!

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        Última execução em <span className="font-semibold text-foreground">{formatarInstante(ultima.executada_em)}</span>
        {ultima.modelo && (
          <>
            , com <span className="font-semibold text-foreground">{ultima.modelo}</span>
          </>
        )}
        , em {formatarNumero(ultima.duracao_ms / 60_000)} min
      </p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        <CartaoKpi
          titulo="Casos aprovados"
          valor={`${ultima.casos_aprovados} de ${ultima.total_casos}`}
          detalhe={`${formatarNumero((ultima.casos_aprovados / ultima.total_casos) * 100)}% do golden set`}
        />
        {metasAvaliacao.map((meta) => (
          <CartaoMeta key={meta.chave} meta={meta} execucao={ultima} />
        ))}
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

const ComoRodar = () => (
  <p className="text-sm text-muted-foreground">
    Rode <code className="rounded bg-muted px-1 py-0.5 text-foreground">{COMANDO}</code> na pasta ai-agent.
  </p>
)

function AvaliacaoAgentePage() {
  const consulta = useAvaliacoesAgente()
  const mensagemVazio = 'Nenhuma avaliação gravada ainda.'

  return (
    <section className="flex flex-col gap-6">
      <CabecalhoPagina />

      <Nota titulo="Como funciona">
        Cada execução faz ao agente as perguntas do golden set, com resposta conhecida, usando o modelo e o banco de
        verdade, e compara o resultado com o esperado. Essas perguntas não entram no uso do agente. Para rodar de novo
        (alguns minutos e tokens do modelo), use <code className="rounded bg-muted px-1 py-0.5">{COMANDO}</code> na
        pasta ai-agent.
      </Nota>

      <EstadoConsulta
        consulta={consulta}
        estaVazio={semExecucoes}
        mensagemVazio={mensagemVazio}
        acaoVazio={<ComoRodar />}
        esqueleto={<KpisEsqueleto />}
      >
        {(dados) => <UltimaExecucao dados={dados} />}
      </EstadoConsulta>

      <BlocoDados
        titulo="Evolução por execução"
        descricao="As 30 execuções mais recentes; a linha tracejada é a meta"
        consulta={consulta}
        estaVazio={semExecucoes}
        mensagemVazio={mensagemVazio}
      >
        {(dados) => <EvolucaoAvaliacoes execucoes={dados.execucoes} />}
      </BlocoDados>

      <BlocoDados
        titulo="Casos da última execução"
        descricao="Cada pergunta do golden set, o que ela espera do agente e por que passou ou falhou"
        consulta={consulta}
        estaVazio={semExecucoes}
        mensagemVazio={mensagemVazio}
      >
        {(dados) => <CasosAvaliacao casos={dados.casos} />}
      </BlocoDados>
    </section>
  )
}

export default AvaliacaoAgentePage
