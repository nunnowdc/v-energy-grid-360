import { CartesianGrid, Line, LineChart, XAxis, YAxis } from 'recharts'
import Variacao from '@/components/Variacao/Variacao'
import { ChartContainer, ChartTooltip, type ChartConfig } from '@/components/ui/chart'
import { variacaoPercentual } from '@/lib/comparacao'
import { formatarCompetencia, formatarCompetenciaCurta, formatarPeriodo } from '@/lib/formatacao'
import { cn } from '@/lib/utils'

// Período escolhido em petróleo e o anterior em cinza (decisão de design para dois períodos)
const configuracao = {
  atual: { label: 'Período escolhido', color: 'var(--primary)' },
  anterior: { label: 'Período anterior', color: 'var(--chart-anterior)' },
} satisfies ChartConfig

// Um mês com as medidas numéricas, ex.: { mes_referencia, receita_faturada, consumo_kwh }
type Mes = { mes_referencia: string }

export type MedidaMensal<T extends Mes> = {
  chave: { [C in keyof T]: T[C] extends number ? C : never }[keyof T]
  // Com a unidade, ex.: "Receita faturada (R$)"
  titulo: string
  formatar: (valor: number) => string
}

// Um ponto do eixo: o mês do período escolhido e o mês na mesma posição do anterior
type PontoMes = {
  mes: string
  mesAnterior?: string
  atual: number
  anterior?: number
}

function pontos<T extends Mes>(atual: T[], anterior: T[], chave: MedidaMensal<T>['chave']): PontoMes[] {
  return atual.map((mes, indice) => ({
    mes: mes.mes_referencia,
    mesAnterior: anterior[indice]?.mes_referencia,
    atual: mes[chave] as number,
    anterior: anterior[indice]?.[chave] as number | undefined,
  }))
}

function Dica({ ponto, formatar }: { ponto: PontoMes; formatar: (valor: number) => string }) {
  const linhas = [
    { chave: 'atual' as const, mes: ponto.mes, valor: ponto.atual },
    { chave: 'anterior' as const, mes: ponto.mesAnterior, valor: ponto.anterior },
  ]
  const variacao = ponto.anterior === undefined ? undefined : variacaoPercentual(ponto.atual, ponto.anterior)

  return (
    <div className="grid min-w-44 gap-1.5 rounded-lg border border-border/50 bg-background px-2.5 py-1.5 text-xs shadow-xl">
      {linhas.map(
        ({ chave, mes, valor }) =>
          mes !== undefined &&
          valor !== undefined && (
            <div key={chave} className="flex items-center justify-between gap-4">
              <span className="flex items-center gap-1.5 text-muted-foreground">
                <span className="size-2.5 rounded-[2px]" style={{ background: configuracao[chave].color }} />
                {formatarCompetencia(mes)}
              </span>
              <span className="tabular-nums font-medium text-foreground">{formatar(valor)}</span>
            </div>
          ),
      )}
      {variacao !== undefined && (
        <div className="border-t pt-1.5">
          <Variacao percentual={variacao} />
        </div>
      )}
    </div>
  )
}

type GraficoMedidaProps = {
  titulo: string
  dados: PontoMes[]
  formatar: (valor: number) => string
  sincronia: string
  // Só o gráfico de baixo mostra os meses: os dois dividem o mesmo eixo
  mostrarMeses?: boolean
}

function GraficoMedida({ titulo, dados, formatar, sincronia, mostrarMeses }: GraficoMedidaProps) {
  return (
    <div className="flex flex-col gap-1">
      <h3 className="text-[13px] font-medium text-muted-foreground">{titulo}</h3>
      <ChartContainer config={configuracao} className={cn('aspect-auto w-full', mostrarMeses ? 'h-44' : 'h-36')}>
        <LineChart data={dados} syncId={sincronia} margin={{ top: 6, left: 4, right: 12 }}>
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey="mes"
            hide={!mostrarMeses}
            tickLine={false}
            axisLine={false}
            tickFormatter={formatarCompetenciaCurta}
          />
          {/* Linhas não precisam começar no zero; a largura fixa alinha os dois gráficos */}
          <YAxis width={92} domain={['auto', 'auto']} tickLine={false} axisLine={false} tickFormatter={formatar} />
          <ChartTooltip
            cursor={{ stroke: 'var(--border)' }}
            content={({ active, payload }) =>
              active && payload?.length ? <Dica ponto={payload[0].payload as PontoMes} formatar={formatar} /> : null
            }
          />
          <Line dataKey="anterior" stroke="var(--color-anterior)" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
          <Line dataKey="atual" stroke="var(--color-atual)" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
        </LineChart>
      </ChartContainer>
    </div>
  )
}

function textoPeriodo(meses: Mes[]) {
  return meses.length > 0 ? formatarPeriodo(meses[0].mes_referencia, meses.at(-1)!.mes_referencia) : ''
}

type GraficosMensaisProps<T extends Mes> = {
  atual: T[]
  // Mesmo tamanho e mesma ordem: o 1º mês do atual se compara ao 1º do anterior
  anterior: T[]
  // De cima para baixo, ex.: receita em cima e consumo embaixo
  medidas: [MedidaMensal<T>, MedidaMensal<T>]
  // Liga a dica dos dois gráficos (cada tela usa o seu)
  sincronia: string
}

// Duas medidas empilhadas que dividem o eixo dos meses (nunca dois eixos Y no
// mesmo gráfico). O período anterior aparece em cinza na mesma posição
function GraficosMensais<T extends Mes>({ atual, anterior, medidas, sincronia }: GraficosMensaisProps<T>) {
  const legenda = [
    { chave: 'atual' as const, texto: textoPeriodo(atual) },
    { chave: 'anterior' as const, texto: textoPeriodo(anterior) },
  ]

  return (
    <div className="flex flex-col gap-4">
      {medidas.map((medida, indice) => (
        <GraficoMedida
          key={String(medida.chave)}
          titulo={medida.titulo}
          dados={pontos(atual, anterior, medida.chave)}
          formatar={medida.formatar}
          sincronia={sincronia}
          mostrarMeses={indice === medidas.length - 1}
        />
      ))}
      <ul className="flex flex-wrap justify-center gap-x-5 gap-y-1 text-xs text-muted-foreground">
        {legenda.map(({ chave, texto }) => (
          <li key={chave} className="flex items-center gap-1.5">
            <span className="h-0.5 w-4 rounded-full" style={{ background: configuracao[chave].color }} />
            {configuracao[chave].label}: {texto}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default GraficosMensais
