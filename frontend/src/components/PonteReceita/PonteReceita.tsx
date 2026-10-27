import { Bar, BarChart, CartesianGrid, Cell, LabelList, XAxis, YAxis } from 'recharts'
import { ChartContainer, type ChartConfig } from '@/components/ui/chart'
import type { DecomposicaoReceita } from '@/hooks/use-receita'
import { formatarMoedaCompacta } from '@/lib/formatacao'

// O eixo já mostra que é R$: o rótulo da barra fica curto ("171,5 mi", "+21,8 mi")
// para caber no celular
const rotuloTotal = new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 1 })
const rotuloEfeito = new Intl.NumberFormat('pt-BR', {
  notation: 'compact',
  maximumFractionDigits: 1,
  signDisplay: 'exceptZero',
})

// Receitas dos dois períodos em petróleo e os efeitos em cinza (decisão de design)
const configuracao = {
  total: { label: 'Receita do período', color: 'var(--primary)' },
  efeito: { label: 'Efeito na variação', color: 'var(--chart-anterior)' },
} satisfies ChartConfig

type Degrau = {
  nome: string
  // Parte invisível que levanta a barra do efeito até onde o degrau anterior parou
  base: number
  altura: number
  rotulo: string
  tipo: keyof typeof configuracao
}

function degraus({ receita_p0, receita_p1, efeito_volume, efeito_preco }: DecomposicaoReceita): Degrau[] {
  const depoisDoVolume = receita_p0 + efeito_volume
  const efeito = (nome: string, de: number, valor: number): Degrau => ({
    nome,
    base: Math.min(de, de + valor),
    altura: Math.abs(valor),
    rotulo: rotuloEfeito.format(valor),
    tipo: 'efeito',
  })

  return [
    { nome: 'Receita base', base: 0, altura: receita_p0, rotulo: rotuloTotal.format(receita_p0), tipo: 'total' },
    efeito('Efeito volume', receita_p0, efeito_volume),
    efeito('Efeito preço', depoisDoVolume, efeito_preco),
    {
      nome: 'Receita comparada',
      base: 0,
      altura: receita_p1,
      rotulo: rotuloTotal.format(receita_p1),
      tipo: 'total',
    },
  ]
}

type PropsRotuloEixo = { x?: number; y?: number; payload?: { value: string } }

// Nome do degrau em duas linhas ("Efeito" / "volume") para caber no celular
function RotuloEixo({ x = 0, y = 0, payload }: PropsRotuloEixo) {
  const [primeira, ...resto] = (payload?.value ?? '').split(' ')
  return (
    <text x={x} y={y + 12} textAnchor="middle" className="fill-muted-foreground text-xs">
      <tspan x={x}>{primeira}</tspan>
      <tspan x={x} dy="1.2em">
        {resto.join(' ')}
      </tspan>
    </text>
  )
}

type PonteReceitaProps = {
  total: DecomposicaoReceita
}

// Cascata da receita: parte da receita base, soma o efeito volume e o efeito preço
// e chega na receita comparada. Os valores ficam escritos em cima de cada barra
function PonteReceita({ total }: PonteReceitaProps) {
  const dados = degraus(total)

  return (
    <div className="flex flex-col gap-3">
      <ChartContainer config={configuracao} className="aspect-auto h-72 w-full">
        <BarChart data={dados} barCategoryGap="30%" margin={{ top: 24, left: 4, right: 4 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="nome" interval={0} height={40} tickLine={false} axisLine={false} tick={<RotuloEixo />} />
          <YAxis width={68} tickLine={false} axisLine={false} tickFormatter={formatarMoedaCompacta} />
          <Bar dataKey="base" stackId="ponte" fill="transparent" />
          <Bar dataKey="altura" stackId="ponte" radius={4}>
            {dados.map((degrau) => (
              <Cell key={degrau.nome} fill={`var(--color-${degrau.tipo})`} />
            ))}
            <LabelList dataKey="rotulo" position="top" className="fill-foreground text-[11px] font-semibold tabular-nums" />
          </Bar>
        </BarChart>
      </ChartContainer>
      <ul className="flex flex-wrap justify-center gap-x-5 gap-y-1 text-xs text-muted-foreground">
        {Object.entries(configuracao).map(([chave, { label, color }]) => (
          <li key={chave} className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-[2px]" style={{ background: color }} />
            {label}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default PonteReceita
