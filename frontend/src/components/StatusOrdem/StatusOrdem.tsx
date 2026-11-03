import { CircleCheck, CircleDashed, CircleX, Truck } from 'lucide-react'
import Etiqueta, { type TomEtiqueta } from '@/components/Etiqueta/Etiqueta'
import type { StatusOrdem as Status } from '@/hooks/use-ordens-inspecao'

const aparencia: Record<Status, { texto: string; Icone: typeof Truck; tom: TomEtiqueta }> = {
  // Aberta espera alguém enviar a equipe; em campo já está andando
  ABERTA: { texto: 'Aberta', Icone: CircleDashed, tom: 'atencao' },
  EM_CAMPO: { texto: 'Em campo', Icone: Truck, tom: 'andamento' },
  CONCLUIDA: { texto: 'Concluída', Icone: CircleCheck, tom: 'positivo' },
  CANCELADA: { texto: 'Cancelada', Icone: CircleX, tom: 'neutro' },
}

// Situação da ordem numa etiqueta com cor, ícone e texto
function StatusOrdem({ status }: { status: Status }) {
  const { texto, Icone, tom } = aparencia[status]

  return (
    <Etiqueta tom={tom} Icone={Icone}>
      {texto}
    </Etiqueta>
  )
}

export default StatusOrdem
