import { Info, TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

// info: regra para ler a tela; atencao: cuidado ao tirar conclusão dos números
type TomNota = 'info' | 'atencao'

const aparencia: Record<TomNota, { Icone: typeof Info; caixa: string; icone: string }> = {
  info: { Icone: Info, caixa: 'border-primary/20 bg-primary/5', icone: 'text-primary' },
  atencao: { Icone: TriangleAlert, caixa: 'border-atencao/25 bg-atencao-fundo', icone: 'text-atencao' },
}

type NotaProps = {
  tom?: TomNota
  // Resumo em negrito, ex.: "Como ler DEC e FEC"
  titulo: string
  children: ReactNode
}

// Caixa de aviso no topo da tela, com ícone, título e o texto da regra
function Nota({ tom = 'info', titulo, children }: NotaProps) {
  const { Icone, caixa, icone } = aparencia[tom]

  return (
    <div role="note" className={cn('flex items-start gap-2.5 rounded-md border px-3 py-2.5 text-sm', caixa)}>
      <Icone aria-hidden="true" className={cn('mt-0.5 size-4 shrink-0', icone)} />
      <p className="text-foreground/85">
        <span className="font-semibold text-foreground">{titulo}.</span> {children}
      </p>
    </div>
  )
}

export default Nota
