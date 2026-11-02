import { CartesianGrid, LabelList, Line, LineChart, XAxis, YAxis } from 'recharts'
import { ChartContainer, ChartTooltip, type ChartConfig } from '@/components/ui/chart'
import type { DiaUsoAgente } from '@/hooks/use-uso-agente'
import { formatarData, formatarDiaMes, formatarNumero, formatarNumeroCompacto, formatarSegundos } from '@/lib/formatacao'
import { cn } from '@/lib/utils'

const configuracao = {
  valor: { label: 'Valor do dia', color: 'var(--primary)' },
} satisfies ChartConfig

// Acima disso, os números escritos em cada ponto se sobrepõem: ficam só na dica
const MAXIMO_DIAS_COM_ROTULO = 12

type Medida = {
  chave: 'tempo_medio_ms' | 'tokens_total'
  // Com a unidade, ex.: "Tempo médio de resposta (s)"
  titulo: string
  // Curto, para o eixo e os pontos (ex.: "499,9 mil")
  formatarCurto: (valor: number) => string
  // Completo, para a dica (ex.: "499.876")
  formatar: (valor: number) => string
}

const medidas: [Medida, Medida] = [
  {
    chave: 'tempo_medio_ms',
    titulo: 'Tempo médio de resposta (s)',
    formatarCurto: formatarSegundos,
    formatar: formatarSegundos,
  },
  {
    chave: 'tokens_total',
    titulo: 'Tokens usados no dia',
    formatarCurto: formatarNumeroCompacto,
    formatar: formatarNumero,
  },
]

type Ponto = { dia: string; perguntas: number; valor: number }

// O número de cada ponto numa etiqueta com o fundo do cartão: a linha que sobe ou desce
// passa por trás dela, sem cortar o texto. Fica acima do ponto
function Etiqueta({ x, y, texto }: { x: number; y: number; texto: string }) {
  // Largura aproximada do texto em 12px semibold, mais a folga dos lados
  const largura = texto.length * 7 + 12
  const altura = 20
  const topo = y - altura - 8

  return (
    <g>
      <rect
        x={x - largura / 2}
        y={topo}
        width={largura}
        height={altura}
        rx={5}
        fill="var(--card)"
        stroke="var(--border)"
      />
      <text
        x={x}
        y={topo + altura / 2}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={12}
        fontWeight={600}
        fill="var(--foreground)"
        className="tabular-nums"
      >
        {texto}
      </text>
    </g>
  )
}

function Dica({ ponto, formatar }: { ponto: Ponto; formatar: (valor: number) => string }) {
  return (
    <div className="grid min-w-36 gap-1 rounded-lg border border-border/50 bg-background px-2.5 py-1.5 text-xs shadow-xl">
      <span className="font-medium text-foreground">{formatarData(ponto.dia)}</span>
      <span className="tabular-nums text-foreground">{formatar(ponto.valor)}</span>
      <span className="text-muted-foreground">
        {ponto.perguntas === 1 ? '1 pergunta' : `${formatarNumero(ponto.perguntas)} perguntas`}
      </span>
    </div>
  )
}

type GraficoProps = Medida & { dias: DiaUsoAgente[]; mostrarDias: boolean }

function Grafico({ chave, titulo, formatarCurto, formatar, dias, mostrarDias }: GraficoProps) {
  const pontos: Ponto[] = dias.map((dia) => ({ dia: dia.dia, perguntas: dia.perguntas, valor: dia[chave] ?? 0 }))
  const comRotulos = pontos.length <= MAXIMO_DIAS_COM_ROTULO

  return (
    <div className="flex flex-col gap-1">
      <h3 className="text-[13px] font-medium text-muted-foreground">{titulo}</h3>
      <ChartContainer config={configuracao} className={cn('aspect-auto w-full', mostrarDias ? 'h-40' : 'h-32')}>
        <LineChart data={pontos} syncId="agente-por-dia" margin={{ top: comRotulos ? 32 : 6, left: 4, right: 24 }}>
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey="dia"
            hide={!mostrarDias}
            tickLine={false}
            axisLine={false}
            tickFormatter={formatarDiaMes}
            padding={{ left: 32, right: 32 }}
            minTickGap={16}
          />
          {/* A largura fixa alinha os dois gráficos */}
          <YAxis width={64} domain={[0, 'auto']} tickLine={false} axisLine={false} tickFormatter={formatarCurto} />
          <ChartTooltip
            cursor={{ stroke: 'var(--border)' }}
            content={({ active, payload }) =>
              active && payload?.length ? <Dica ponto={payload[0].payload as Ponto} formatar={formatar} /> : null
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
                content={({ x, y, value }) => (
                  <Etiqueta x={Number(x)} y={Number(y)} texto={formatarCurto(Number(value))} />
                )}
              />
            )}
          </Line>
        </LineChart>
      </ChartContainer>
    </div>
  )
}

// Tempo médio e tokens gastos em cada dia com perguntas, empilhados e com o mesmo eixo
// dos dias (nunca dois eixos Y). Os dias sem uso ficam de fora: o gráfico de perguntas
// ao lado já mostra quando o agente não foi usado
function TempoTokensPorDia({ dias }: { dias: DiaUsoAgente[] }) {
  const comPerguntas = dias.filter((dia) => dia.perguntas > 0)

  return (
    <div className="flex flex-col gap-3">
      {medidas.map((medida, indice) => (
        <Grafico key={medida.chave} {...medida} dias={comPerguntas} mostrarDias={indice === medidas.length - 1} />
      ))}
    </div>
  )
}

export default TempoTokensPorDia
