import { CircleCheck } from 'lucide-react'
import StatusPagamento from '@/components/StatusPagamento/StatusPagamento'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { Uc360 } from '@/hooks/use-uc-360'
import { formatarCompetencia, formatarData, formatarMoeda } from '@/lib/formatacao'

type FaturasEmAbertoProps = {
  dados: Pick<Uc360, 'faturas_em_aberto' | 'resumo_faturas_em_aberto'>
  className?: string
}

// Quantas faturas aguardam pagamento, quanto somam e quais são
function FaturasEmAberto({ dados, className }: FaturasEmAbertoProps) {
  const { faturas_em_aberto: faturas, resumo_faturas_em_aberto: resumo } = dados

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-[15px] font-semibold">Faturas em aberto</CardTitle>
        <CardDescription>Pendentes e atrasadas</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {resumo.quantidade === 0 ? (
          <p className="flex items-center gap-2 text-muted-foreground">
            <CircleCheck aria-hidden="true" className="size-4" />
            Nenhuma fatura em aberto.
          </p>
        ) : (
          <>
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-[28px] leading-none font-semibold tracking-tight">
                {resumo.valor_total === null ? '—' : formatarMoeda(resumo.valor_total)}
              </span>
              <span className="text-muted-foreground">
                em {resumo.quantidade} {resumo.quantidade === 1 ? 'fatura' : 'faturas'}
              </span>
            </div>
            <ul className="flex max-h-72 flex-col divide-y overflow-y-auto">
              {faturas.map((fatura) => (
                <li key={fatura.id_fatura} className="flex items-center justify-between gap-3 py-2 text-[13px]">
                  <div className="flex flex-col">
                    <span className="font-medium">{formatarCompetencia(fatura.mes_referencia)}</span>
                    <span className="text-xs text-muted-foreground">
                      {fatura.status_pagamento === 'ATRASADA' ? 'Venceu em' : 'Vence em'}{' '}
                      {fatura.data_vencimento ? formatarData(fatura.data_vencimento) : '—'}
                    </span>
                  </div>
                  <div className="flex flex-col items-end">
                    <span className="font-mono">
                      {fatura.receita_faturada === null ? '—' : formatarMoeda(fatura.receita_faturada)}
                    </span>
                    <StatusPagamento status={fatura.status_pagamento} />
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </CardContent>
    </Card>
  )
}

export default FaturasEmAberto
