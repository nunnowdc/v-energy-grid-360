import MiniTendencia from '@/components/MiniTendencia/MiniTendencia'
import Variacao from '@/components/Variacao/Variacao'
import { Card, CardContent, CardDescription, CardHeader } from '@/components/ui/card'

type CartaoKpiProps = {
  titulo: string
  // Valor já formatado (ex.: "R$ 169,7 mi"), para cada tela escolher o formato
  valor: string
  // Percentual em pontos (8 = 8%)
  variacao?: number
  complementoVariacao?: string
  detalhe?: string
  // Valores do período para a minitendência (ex.: os 12 meses)
  tendencia?: number[]
}

function CartaoKpi({ titulo, valor, variacao, complementoVariacao, detalhe, tendencia }: CartaoKpiProps) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardDescription className="text-[13px] font-medium">{titulo}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <span className="tabular-nums text-[28px] leading-none font-semibold tracking-tight">{valor}</span>
        <div className="flex items-end justify-between gap-3">
          <div className="flex flex-col gap-1">
            {variacao !== undefined && (
              <Variacao percentual={variacao} complemento={complementoVariacao} />
            )}
            {detalhe && <span className="text-xs text-muted-foreground">{detalhe}</span>}
          </div>
          {tendencia && tendencia.length > 0 && <MiniTendencia valores={tendencia} />}
        </div>
      </CardContent>
    </Card>
  )
}

export default CartaoKpi
