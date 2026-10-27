import { bandeirasTarifarias, type BandeiraTarifaria } from '@/config/bandeiras'

type SeloBandeiraProps = {
  bandeira: BandeiraTarifaria | null
}

// Bandeira tarifária: a cor sempre acompanhada do nome
function SeloBandeira({ bandeira }: SeloBandeiraProps) {
  if (!bandeira) {
    return <span className="text-muted-foreground">—</span>
  }
  const { label, cor } = bandeirasTarifarias[bandeira]

  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <span aria-hidden="true" className="size-2 rounded-full" style={{ backgroundColor: cor }} />
      {label}
    </span>
  )
}

export default SeloBandeira
