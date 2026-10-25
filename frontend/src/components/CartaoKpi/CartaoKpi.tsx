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
}

function CartaoKpi({ titulo, valor, variacao, complementoVariacao, detalhe }: CartaoKpiProps) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardDescription>{titulo}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-1">
        <span className="text-2xl font-semibold tabular-nums">{valor}</span>
        {variacao !== undefined && (
          <Variacao percentual={variacao} complemento={complementoVariacao} />
        )}
        {detalhe && <span className="text-xs text-muted-foreground">{detalhe}</span>}
      </CardContent>
    </Card>
  )
}

export default CartaoKpi
