import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

// Formato do CartaoKpi enquanto os dados carregam
function CartaoKpiEsqueleto() {
  return (
    <Card size="sm">
      <CardHeader>
        <Skeleton className="h-4 w-2/3" />
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <Skeleton className="h-7 w-1/2" />
        <Skeleton className="h-4 w-3/4" />
      </CardContent>
    </Card>
  )
}

export default CartaoKpiEsqueleto
