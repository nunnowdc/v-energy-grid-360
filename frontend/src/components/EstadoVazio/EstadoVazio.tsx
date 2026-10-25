import { SearchX } from 'lucide-react'
import type { ReactNode } from 'react'

type EstadoVazioProps = {
  mensagem?: string
  // Ex.: botão "Limpar filtros"
  acao?: ReactNode
}

function EstadoVazio({
  mensagem = 'Nenhum dado para os filtros selecionados.',
  acao,
}: EstadoVazioProps) {
  return (
    <div className="flex min-h-40 flex-col items-center justify-center gap-2 text-center">
      <SearchX className="size-8 text-muted-foreground" />
      <p className="font-medium">{mensagem}</p>
      {acao}
    </div>
  )
}

export default EstadoVazio
