import { CartesianGrid, LabelList, Line, LineChart, ReferenceLine, XAxis, YAxis } from 'recharts'
import EtiquetaPonto from '@/components/EtiquetaPonto/EtiquetaPonto'
import { ChartContainer, ChartTooltip, type ChartConfig } from '@/components/ui/chart'
import { metasAvaliacao, type MetaAvaliacao } from '@/config/metas-avaliacao'
import type { ExecucaoAvaliacao } from '@/hooks/use-avaliacoes-agente'
import { formatarInstante, formatarInstanteCurto, formatarNumero } from '@/lib/formatacao'

const configuracao = {
  valor: { label: 'Resultado da execução', color: 'var(--primary)' },
} satisfies ChartConfig

// Acima disso, os números escritos em cada ponto se sobrepõem: ficam só na dica
const MAXIMO_PONTOS_COM_ROTULO = 12

type Ponto = { id: string; executada_em: string; modelo: string | null; valor: number | null }

const formatarValor = (meta: MetaAvaliacao, valor: number) =>
  meta.sentido === 'maximo' ? formatarNumero(Math.round(valor)) : `${formatarNumero(valor)}%`

function Dica({ ponto, meta }: { ponto: Ponto; meta: MetaAvaliacao }) {
  return (
    <div className="grid min-w-40 gap-1 rounded-lg border border-border/50 bg-background px-2.5 py-1.5 text-xs shadow-xl">
      <span className="font-medium text-foreground">{formatarInstante(ponto.executada_em)}</span>
      <span className="tabular-nums text-foreground">
        {ponto.valor === null ? 'Sem casos desse tipo' : formatarValor(meta, ponto.valor)}
      </span>
      <span className="text-muted-foreground">Meta: {meta.textoMeta}</span>
      {ponto.modelo && <span className="text-muted-foreground">{ponto.modelo}</span>}
    </div>
  )
}

function Grafico({ meta, execucoes }: { meta: MetaAvaliacao; execucoes: ExecucaoAvaliacao[] }) {
  const pontos: Ponto[] = execucoes.map((execucao) => ({
    id: execucao.id,
    executada_em: execucao.executada_em,
    modelo: execucao.modelo,
    valor: execucao[meta.chave],
  }))
  const comRotulos = pontos.length <= MAXIMO_PONTOS_COM_ROTULO
  const percentual = meta.sentido === 'minimo'

  return (
    <div className="flex flex-col gap-1">
      <h3 className="text-[13px] font-medium text-muted-foreground">
        {meta.titulo} <span className="font-normal">· meta: {meta.textoMeta}</span>
      </h3>
      <ChartContainer config={configuracao} className="aspect-auto h-40 w-full">
        <LineChart data={pontos} margin={{ top: comRotulos ? 32 : 6, left: 4, right: 24 }}>
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey="id"
            tickLine={false}
            axisLine={false}
            tickFormatter={(id: string) => formatarInstanteCurto(pontos.find((ponto) => ponto.id === id)!.executada_em)}
            padding={{ left: 32, right: 32 }}
            minTickGap={16}
          />
          <YAxis
            width={48}
            domain={percentual ? [0, 100] : [0, 'auto']}
            ticks={percentual ? [0, 50, 100] : undefined}
            tickLine={false}
            axisLine={false}
            tickFormatter={(valor: number) => (percentual ? `${valor}%` : formatarNumero(valor))}
          />
          {/* A meta tracejada; com tokens acima dela, o eixo cresce para mostrar as duas */}
          <ReferenceLine y={meta.meta} stroke="var(--muted-foreground)" strokeDasharray="4 4" ifOverflow="extendDomain" />
          <ChartTooltip
            cursor={{ stroke: 'var(--border)' }}
            content={({ active, payload }) =>
              active && payload?.length ? <Dica ponto={payload[0].payload as Ponto} meta={meta} /> : null
            }
          />
          <Line
            dataKey="valor"
            stroke="var(--color-valor)"
            strokeWidth={2}
            dot={{ r: 3, fill: 'var(--color-valor)' }}
            activeDot={{ r: 4 }}
          >
            {comRotulos && (
              <LabelList
                dataKey="valor"
                content={({ x, y, value }) =>
                  value === null || value === undefined ? null : (
                    <EtiquetaPonto x={Number(x)} y={Number(y)} texto={formatarValor(meta, Number(value))} />
                  )
                }
              />
            )}
          </Line>
        </LineChart>
      </ChartContainer>
    </div>
  )
}

// Uma métrica por gráfico, cada um com a sua meta tracejada (nunca dois eixos Y)
function EvolucaoAvaliacoes({ execucoes }: { execucoes: ExecucaoAvaliacao[] }) {
  return (
    <div className="grid gap-x-6 gap-y-4 md:grid-cols-2">
      {metasAvaliacao.map((meta) => (
        <Grafico key={meta.chave} meta={meta} execucoes={execucoes} />
      ))}
    </div>
  )
}

export default EvolucaoAvaliacoes
