import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

// andamento: em execução (ex.: ordem em campo); atencao: esperando alguém agir
// (ex.: ordem aberta, fatura pendente); positivo: resolvido; negativo: problema
export type TomEtiqueta = 'neutro' | 'andamento' | 'atencao' | 'positivo' | 'negativo'

const cores: Record<TomEtiqueta, string> = {
  neutro: 'bg-muted text-muted-foreground',
  andamento: 'bg-primary/10 text-primary',
  atencao: 'bg-atencao-fundo text-atencao',
  positivo: 'bg-positivo-fundo text-positivo',
  negativo: 'bg-negativo-fundo text-negativo',
}

type EtiquetaProps = {
  tom: TomEtiqueta
  Icone: LucideIcon
  children: ReactNode
  className?: string
}

// Situação numa pílula com fundo, ícone e texto: dá para ler a coluna de relance,
// e a cor nunca aparece sozinha (decisão de design)
function Etiqueta({ tom, Icone, children, className }: EtiquetaProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap',
        cores[tom],
        className,
      )}
    >
      <Icone aria-hidden="true" className="size-3.5" />
      {children}
    </span>
  )
}

export default Etiqueta
