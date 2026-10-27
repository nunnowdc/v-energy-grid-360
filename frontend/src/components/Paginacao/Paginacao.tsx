import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { formatarNumero } from '@/lib/formatacao'

type PaginacaoProps = {
  pagina: number
  limite: number
  total: number
  // Ex.: "faturas", para o texto "1–10 de 48 faturas"
  nomeItens: string
  aoMudar: (pagina: number) => void
  desabilitado?: boolean
}

function Paginacao({ pagina, limite, total, nomeItens, aoMudar, desabilitado }: PaginacaoProps) {
  const totalPaginas = Math.max(1, Math.ceil(total / limite))
  const primeiro = total === 0 ? 0 : (pagina - 1) * limite + 1
  const ultimo = Math.min(pagina * limite, total)

  return (
    <div className="flex items-center justify-between gap-3 pt-3 text-[13px] text-muted-foreground">
      <span className="font-mono">
        {primeiro}–{ultimo} de {formatarNumero(total)} {nomeItens}
      </span>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="sm"
          disabled={desabilitado || pagina <= 1}
          onClick={() => aoMudar(pagina - 1)}
        >
          <ChevronLeft />
          Anterior
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={desabilitado || pagina >= totalPaginas}
          onClick={() => aoMudar(pagina + 1)}
        >
          Próxima
          <ChevronRight />
        </Button>
      </div>
    </div>
  )
}

export default Paginacao
