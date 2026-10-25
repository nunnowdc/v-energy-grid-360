import { RotateCw, TriangleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'

type EstadoErroProps = {
  mensagem: string
  aoTentarDeNovo: () => void
}

// O erro fica dentro do bloco: o resto da tela continua funcionando
function EstadoErro({ mensagem, aoTentarDeNovo }: EstadoErroProps) {
  return (
    <div role="alert" className="flex min-h-40 flex-col items-center justify-center gap-2 text-center">
      <TriangleAlert className="size-8 text-muted-foreground" />
      <p className="font-medium">Não foi possível carregar estes dados</p>
      <p className="max-w-sm text-sm text-muted-foreground">{mensagem}</p>
      <Button variant="outline" size="sm" className="mt-1" onClick={aoTentarDeNovo}>
        <RotateCw />
        Tentar de novo
      </Button>
    </div>
  )
}

export default EstadoErro
