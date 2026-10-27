import { rotuloCausa } from '@/config/causas'
import type { ContinuidadeRede } from '@/hooks/use-continuidade'
import { formatarNumero } from '@/lib/formatacao'

type OcorrenciasPorCausaProps = {
  porCausa: ContinuidadeRede['ocorrencias']['por_causa']
}

// Barras horizontais das causas, da que mais interrompe para a que menos.
// Uma cor só (petróleo): a causa é categoria, não precisa de cor própria
function OcorrenciasPorCausa({ porCausa }: OcorrenciasPorCausaProps) {
  const total = porCausa.reduce((soma, item) => soma + item.ocorrencias, 0)
  const maior = Math.max(...porCausa.map((item) => item.ocorrencias), 0)

  return (
    <ul className="flex flex-col gap-3">
      {porCausa.map(({ causa, ocorrencias }) => (
        <li key={causa} className="flex flex-col gap-1">
          <div className="flex items-baseline justify-between gap-3 text-[13px]">
            <span className="font-medium">{rotuloCausa(causa)}</span>
            <span>
              <span className="tabular-nums font-semibold">{formatarNumero(ocorrencias)}</span>
              <span className="ml-1.5 text-xs text-muted-foreground">
                {total > 0 ? `${formatarNumero((ocorrencias / total) * 100)}%` : ''}
              </span>
            </span>
          </div>
          <div aria-hidden="true" className="h-2.5 rounded-r-[4px] bg-muted">
            <div
              className="h-full rounded-r-[4px] bg-primary"
              style={{ width: maior > 0 ? `${(ocorrencias / maior) * 100}%` : 0 }}
            />
          </div>
        </li>
      ))}
    </ul>
  )
}

export default OcorrenciasPorCausa
