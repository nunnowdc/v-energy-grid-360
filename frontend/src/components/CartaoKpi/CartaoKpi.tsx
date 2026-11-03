import MiniTendencia from '@/components/MiniTendencia/MiniTendencia'
import Variacao from '@/components/Variacao/Variacao'
import { Card, CardContent, CardDescription, CardHeader } from '@/components/ui/card'
import { corDoTom, type Sentido, type Tom } from '@/lib/comparacao'
import { cn } from '@/lib/utils'

type CartaoKpiProps = {
  titulo: string
  // Valor já formatado (ex.: "R$ 169,7 mi"), para cada tela escolher o formato
  valor: string
  // Quando o próprio valor é uma variação (ex.: efeito preço), a cor diz se ela é boa ou ruim
  tomValor?: Tom
  // Percentual em pontos (8 = 8%)
  variacao?: number
  // Para que lado a medida melhora (pinta a variação de verde ou vermelho)
  sentido?: Sentido
  complementoVariacao?: string
  detalhe?: string
  // Valores do período para a minitendência (ex.: os 12 meses)
  tendencia?: number[]
}

function CartaoKpi({
  titulo,
  valor,
  tomValor,
  variacao,
  sentido,
  complementoVariacao,
  detalhe,
  tendencia,
}: CartaoKpiProps) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardDescription className="text-[13px] font-medium">{titulo}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <span
          className={cn(
            'tabular-nums text-[28px] leading-none font-semibold tracking-tight',
            tomValor && tomValor !== 'neutro' && corDoTom[tomValor],
          )}
        >
          {valor}
        </span>
        <div className="flex items-end justify-between gap-3">
          <div className="flex flex-col gap-1">
            {variacao !== undefined && (
              <Variacao percentual={variacao} sentido={sentido} complemento={complementoVariacao} />
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
