import { CircleAlert, CircleCheck, Clock } from 'lucide-react'
import type { StatusPagamento as Status } from '@/hooks/use-uc-360'
import { cn } from '@/lib/utils'

const aparencia: Record<Status, { texto: string; Icone: typeof Clock; classe: string }> = {
  PAGA: { texto: 'Paga', Icone: CircleCheck, classe: 'text-muted-foreground' },
  PENDENTE: { texto: 'Pendente', Icone: Clock, classe: 'text-foreground' },
  ATRASADA: { texto: 'Atrasada', Icone: CircleAlert, classe: 'font-semibold text-destructive' },
}

type StatusPagamentoProps = {
  status: Status | null
  // Dias de atraso, mostrados junto de "Atrasada"
  diasAtraso?: number | null
}

// Alerta sempre com ícone e texto, nunca só cor (decisão de design)
function StatusPagamento({ status, diasAtraso }: StatusPagamentoProps) {
  if (!status) {
    return <span className="text-muted-foreground">—</span>
  }
  const { texto, Icone, classe } = aparencia[status]
  const comAtraso = status === 'ATRASADA' && diasAtraso ? ` (${diasAtraso} dias)` : ''

  return (
    <span className={cn('inline-flex items-center gap-1 whitespace-nowrap', classe)}>
      <Icone aria-hidden="true" className="size-3.5" />
      {texto}
      {comAtraso}
    </span>
  )
}

export default StatusPagamento
