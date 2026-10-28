import { CircleCheck, CircleDashed, CircleX, Truck } from 'lucide-react'
import type { StatusOrdem as Status } from '@/hooks/use-ordens-inspecao'
import { cn } from '@/lib/utils'

const aparencia: Record<Status, { texto: string; Icone: typeof Truck; classe: string }> = {
  ABERTA: { texto: 'Aberta', Icone: CircleDashed, classe: 'text-foreground' },
  EM_CAMPO: { texto: 'Em campo', Icone: Truck, classe: 'font-medium text-primary' },
  CONCLUIDA: { texto: 'Concluída', Icone: CircleCheck, classe: 'text-muted-foreground' },
  CANCELADA: { texto: 'Cancelada', Icone: CircleX, classe: 'text-muted-foreground line-through' },
}

// Situação da ordem sempre com ícone e texto, nunca só cor (decisão de design)
function StatusOrdem({ status }: { status: Status }) {
  const { texto, Icone, classe } = aparencia[status]

  return (
    <span className={cn('inline-flex items-center gap-1 whitespace-nowrap', classe)}>
      <Icone aria-hidden="true" className="size-3.5" />
      {texto}
    </span>
  )
}

export default StatusOrdem
