import { cn } from '@/lib/utils'

type MarcaVEnergyProps = {
  className?: string
}

// Posições da grade 3×3 que ficam apagadas; o centro é o ponto de energia
const apagados = new Set([1, 3, 5, 7])
const CENTRO = 4

// Marca do portal: a grade da rede elétrica com um ponto de energia no centro
function MarcaVEnergy({ className }: MarcaVEnergyProps) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        'grid size-8 shrink-0 grid-cols-3 gap-[3px] rounded-lg bg-sidebar-primary p-[7px]',
        className,
      )}
    >
      {Array.from({ length: 9 }, (_, posicao) => (
        <span
          key={posicao}
          className={cn(
            'rounded-[1px]',
            posicao === CENTRO ? 'bg-marca-energia' : 'bg-marca-grade',
            apagados.has(posicao) && 'opacity-45',
          )}
        />
      ))}
    </span>
  )
}

export default MarcaVEnergy
