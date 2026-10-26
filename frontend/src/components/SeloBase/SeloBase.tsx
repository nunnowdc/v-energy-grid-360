import { useOpcoesFiltros } from '@/hooks/use-opcoes-filtros'
import { formatarCompetencia } from '@/lib/formatacao'

// Período coberto pela base, sempre à vista: os dados não são "de hoje"
function SeloBase() {
  const { data } = useOpcoesFiltros()
  const primeira = data?.competencias[0]
  const ultima = data?.competencias.at(-1)

  if (!primeira || !ultima) {
    return null
  }

  return (
    <span
      title="Período coberto pela base de dados"
      className="inline-flex items-center gap-2 rounded-full border bg-muted px-3 py-1 font-mono text-xs text-foreground/80 uppercase"
    >
      <span aria-hidden="true" className="size-1.5 rounded-full bg-primary" />
      Base {formatarCompetencia(primeira)} – {formatarCompetencia(ultima)}
    </span>
  )
}

export default SeloBase
