import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'
import type { ConsumoMes } from '@/hooks/use-uc-360'
import { formatarCompetencia, formatarCompetenciaCurta, formatarKwh, formatarNumero } from '@/lib/formatacao'

// Período atual em petróleo e o anterior em cinza (decisão de design para dois períodos)
const configuracao = {
  atual: { label: 'Consumo do mês', color: 'var(--primary)' },
  anterior: { label: 'Mesmo mês do ano anterior', color: 'var(--chart-anterior)' },
} satisfies ChartConfig

type ConsumoDozeMesesProps = {
  meses: ConsumoMes[]
  className?: string
}

// Consumo medido dos últimos 12 meses ao lado do mesmo mês do ano anterior:
// é o que o atendente olha quando o cliente reclama de conta alta
function ConsumoDozeMeses({ meses, className }: ConsumoDozeMesesProps) {
  const dados = meses.map((mes) => ({
    mes: mes.mes_referencia,
    atual: mes.consumo_kwh,
    anterior: mes.consumo_ano_anterior_kwh,
  }))

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-[15px] font-semibold">Consumo dos últimos 12 meses</CardTitle>
        <CardDescription>Consumo medido nas leituras, comparado ao mesmo mês do ano anterior</CardDescription>
      </CardHeader>
      <CardContent>
        {dados.length === 0 ? (
          <p className="text-muted-foreground">Sem leituras nos últimos 12 meses.</p>
        ) : (
          <ChartContainer config={configuracao} className="aspect-auto h-64 w-full">
            <BarChart data={dados} barGap={2} margin={{ left: 4, right: 4 }}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="mes" tickLine={false} axisLine={false} tickFormatter={formatarCompetenciaCurta} />
              <YAxis
                tickLine={false}
                axisLine={false}
                width={44}
                tickFormatter={(valor: number) => formatarNumero(valor)}
              />
              <ChartTooltip
                cursor={{ fill: 'var(--muted)' }}
                content={
                  <ChartTooltipContent
                    labelFormatter={(_, itens) => formatarCompetencia(String(itens[0]?.payload.mes))}
                    formatter={(valor, nome) => (
                      <div className="flex w-full items-center justify-between gap-4">
                        <span className="text-muted-foreground">
                          {configuracao[nome as keyof typeof configuracao].label}
                        </span>
                        <span className="font-mono font-medium text-foreground">
                          {valor === null || valor === undefined ? '—' : formatarKwh(Number(valor))}
                        </span>
                      </div>
                    )}
                  />
                }
              />
              <ChartLegend content={<ChartLegendContent />} />
              <Bar dataKey="anterior" fill="var(--color-anterior)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="atual" fill="var(--color-atual)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  )
}

export default ConsumoDozeMeses
