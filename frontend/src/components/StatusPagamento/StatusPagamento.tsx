import { CircleAlert, CircleCheck, Clock } from 'lucide-react'
import Etiqueta, { type TomEtiqueta } from '@/components/Etiqueta/Etiqueta'
import type { StatusPagamento as Status } from '@/hooks/use-uc-360'

const aparencia: Record<Status, { texto: string; Icone: typeof Clock; tom: TomEtiqueta }> = {
  PAGA: { texto: 'Paga', Icone: CircleCheck, tom: 'positivo' },
  PENDENTE: { texto: 'Pendente', Icone: Clock, tom: 'atencao' },
  ATRASADA: { texto: 'Atrasada', Icone: CircleAlert, tom: 'negativo' },
}

type StatusPagamentoProps = {
  status: Status | null
  // Dias de atraso, mostrados junto de "Atrasada"
  diasAtraso?: number | null
}

// Situação da fatura numa etiqueta com cor, ícone e texto
function StatusPagamento({ status, diasAtraso }: StatusPagamentoProps) {
  if (!status) {
    return <span className="text-muted-foreground">—</span>
  }
  const { texto, Icone, tom } = aparencia[status]
  const comAtraso = status === 'ATRASADA' && diasAtraso ? ` (${diasAtraso} dias)` : ''

  return (
    <Etiqueta tom={tom} Icone={Icone}>
      {texto}
      {comAtraso}
    </Etiqueta>
  )
}

export default StatusPagamento
