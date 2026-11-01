import { corDoTom, tomDaVariacao } from '@/lib/comparacao'
import { formatarMoedaCompactaComSinal } from '@/lib/formatacao'
import { cn } from '@/lib/utils'

type ValorEfeitoProps = {
  reais: number
  className?: string
}

// Efeito na receita com sinal ("-R$ 8,1 mi"): verde quando soma e vermelho quando tira.
// Não quebra linha no meio do valor
function ValorEfeito({ reais, className }: ValorEfeitoProps) {
  const tom = tomDaVariacao(reais, 'subir-e-bom')

  return (
    <span className={cn('tabular-nums whitespace-nowrap', corDoTom[tom], tom !== 'neutro' && 'font-medium', className)}>
      {formatarMoedaCompactaComSinal(reais)}
    </span>
  )
}

export default ValorEfeito
