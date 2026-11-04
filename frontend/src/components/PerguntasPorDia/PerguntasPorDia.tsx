import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from 'recharts'
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'
import type { DiaUsoAgente } from '@/hooks/use-uso-agente'
import { formatarData, formatarDiaMes, formatarNumero } from '@/lib/formatacao'

// De baixo para cima: o que o agente respondeu, o que recusou e onde falhou.
// Erro em vermelho (cor de alerta); recusa em cinza, porque não responder é o
// comportamento esperado quando falta dado seguro. As três cores passaram no validador
// de paleta nos dois temas
const configuracao = {
  respondidas: { label: 'Respondidas', color: 'var(--primary)' },
  recusas: { label: 'Sem resposta segura', color: 'var(--grafico-neutro)' },
  erros: { label: 'Erro ao responder', color: 'var(--grafico-negativo)' },
} satisfies ChartConfig

type Serie = keyof typeof configuracao

// A legenda na ordem das barras (o padrão do recharts é a ordem alfabética)
const ordemSeries = Object.keys(configuracao)

// Perguntas de cada dia, separadas pelo resultado
function PerguntasPorDia({ dias }: { dias: DiaUsoAgente[] }) {
  return (
    <ChartContainer config={configuracao} className="aspect-auto h-64 w-full">
      <BarChart data={dias} margin={{ left: 4, right: 4 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="dia" tickLine={false} axisLine={false} tickFormatter={formatarDiaMes} minTickGap={16} />
        <YAxis
          tickLine={false}
          axisLine={false}
          width={36}
          allowDecimals={false}
          tickFormatter={(valor: number) => formatarNumero(valor)}
        />
        <ChartTooltip
          cursor={{ fill: 'var(--muted)' }}
          content={
            <ChartTooltipContent
              labelFormatter={(_, itens) => formatarData(String(itens[0]?.payload.dia))}
              formatter={(valor, nome) => (
                <div className="flex w-full items-center justify-between gap-4">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    <span
                      className="size-2.5 rounded-[2px]"
                      style={{ background: configuracao[nome as Serie].color }}
                    />
                    {configuracao[nome as Serie].label}
                  </span>
                  <span className="tabular-nums font-medium text-foreground">{formatarNumero(Number(valor))}</span>
                </div>
              )}
            />
          }
        />
        <ChartLegend
          content={<ChartLegendContent />}
          itemSorter={(item) => ordemSeries.indexOf(String(item.dataKey))}
        />
        <Bar dataKey="respondidas" stackId="resultado" fill="var(--color-respondidas)" />
        <Bar dataKey="recusas" stackId="resultado" fill="var(--color-recusas)" />
        <Bar dataKey="erros" stackId="resultado" fill="var(--color-erros)" />
      </BarChart>
    </ChartContainer>
  )
}

export default PerguntasPorDia
