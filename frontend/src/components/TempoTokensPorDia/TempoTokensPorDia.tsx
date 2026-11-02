import { CartesianGrid, Line, LineChart, XAxis, YAxis } from 'recharts'
import { ChartContainer, ChartTooltip, type ChartConfig } from '@/components/ui/chart'
import type { DiaUsoAgente } from '@/hooks/use-uso-agente'
import { formatarData, formatarDiaMes, formatarNumero, formatarSegundos } from '@/lib/formatacao'
import { cn } from '@/lib/utils'

const configuracao = {
  valor: { label: 'Média do dia', color: 'var(--primary)' },
} satisfies ChartConfig

type Medida = {
  chave: 'tempo_medio_ms' | 'tokens_medio'
  // Com a unidade, ex.: "Tempo médio de resposta (s)"
  titulo: string
  formatar: (valor: number) => string
}

const medidas: [Medida, Medida] = [
  { chave: 'tempo_medio_ms', titulo: 'Tempo médio de resposta (s)', formatar: formatarSegundos },
  { chave: 'tokens_medio', titulo: 'Tokens por pergunta', formatar: formatarNumero },
]

type Ponto = { dia: string; valor: number | null }

function Dica({ ponto, formatar }: { ponto: Ponto; formatar: (valor: number) => string }) {
  return (
    <div className="grid min-w-36 gap-1 rounded-lg border border-border/50 bg-background px-2.5 py-1.5 text-xs shadow-xl">
      <span className="font-medium text-foreground">{formatarData(ponto.dia)}</span>
      <span className="tabular-nums text-muted-foreground">
        {ponto.valor === null ? 'Sem perguntas' : formatar(ponto.valor)}
      </span>
    </div>
  )
}

type GraficoProps = Medida & { dias: DiaUsoAgente[]; mostrarDias: boolean }

function Grafico({ chave, titulo, formatar, dias, mostrarDias }: GraficoProps) {
  const pontos: Ponto[] = dias.map((dia) => ({ dia: dia.dia, valor: dia[chave] }))

  return (
    <div className="flex flex-col gap-1">
      <h3 className="text-[13px] font-medium text-muted-foreground">{titulo}</h3>
      <ChartContainer config={configuracao} className={cn('aspect-auto w-full', mostrarDias ? 'h-36' : 'h-28')}>
        <LineChart data={pontos} syncId="agente-por-dia" margin={{ top: 6, left: 4, right: 12 }}>
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey="dia"
            hide={!mostrarDias}
            tickLine={false}
            axisLine={false}
            tickFormatter={formatarDiaMes}
            minTickGap={16}
          />
          {/* A largura fixa alinha os dois gráficos */}
          <YAxis width={64} tickLine={false} axisLine={false} tickFormatter={formatar} />
          <ChartTooltip
            cursor={{ stroke: 'var(--border)' }}
            content={({ active, payload }) =>
              active && payload?.length ? <Dica ponto={payload[0].payload as Ponto} formatar={formatar} /> : null
            }
          />
          {/* Dia sem pergunta fica em branco (não é zero); o ponto aparece mesmo isolado */}
          <Line
            dataKey="valor"
            stroke="var(--color-valor)"
            strokeWidth={2}
            dot={{ r: 3, fill: 'var(--color-valor)' }}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ChartContainer>
    </div>
  )
}

// Tempo e tokens de cada dia, empilhados e com o mesmo eixo dos dias (nunca dois eixos Y)
function TempoTokensPorDia({ dias }: { dias: DiaUsoAgente[] }) {
  return (
    <div className="flex flex-col gap-3">
      {medidas.map((medida, indice) => (
        <Grafico key={medida.chave} {...medida} dias={dias} mostrarDias={indice === medidas.length - 1} />
      ))}
    </div>
  )
}

export default TempoTokensPorDia
