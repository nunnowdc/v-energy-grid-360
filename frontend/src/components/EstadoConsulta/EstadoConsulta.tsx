import type { UseQueryResult } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import EstadoErro from '@/components/EstadoErro/EstadoErro'
import EstadoVazio from '@/components/EstadoVazio/EstadoVazio'
import { Skeleton } from '@/components/ui/skeleton'
import { ErroApi } from '@/lib/api/erro-api'
import { cn } from '@/lib/utils'

export type EstadoConsultaProps<T> = {
  consulta: UseQueryResult<T>
  // Cada tela decide o que é "vazio" (ex.: lista sem itens)
  estaVazio?: (dados: T) => boolean
  mensagemVazio?: string
  acaoVazio?: ReactNode
  // Esqueleto no formato do bloco; sem ele, aparece um retângulo
  esqueleto?: ReactNode
  // Recebe os dados só quando eles existem, então nunca chegam indefinidos
  children: (dados: T) => ReactNode
}

function mensagemDoErro(erro: Error) {
  return erro instanceof ErroApi ? erro.message : 'Algo deu errado. Tente de novo em instantes.'
}

// Os 4 estados de todo bloco de dados: carregando, erro, vazio e
// atualizando (dados anteriores esmaecidos enquanto chega o novo filtro)
function EstadoConsulta<T>({
  consulta,
  estaVazio,
  mensagemVazio,
  acaoVazio,
  esqueleto,
  children,
}: EstadoConsultaProps<T>) {
  if (consulta.isPending) {
    return esqueleto ?? <Skeleton className="h-40 w-full" />
  }

  if (consulta.isError) {
    return (
      <EstadoErro
        mensagem={mensagemDoErro(consulta.error)}
        aoTentarDeNovo={() => consulta.refetch()}
      />
    )
  }

  if (estaVazio?.(consulta.data)) {
    return <EstadoVazio mensagem={mensagemVazio} acao={acaoVazio} />
  }

  return (
    <div
      aria-busy={consulta.isFetching}
      className={cn('transition-opacity', consulta.isFetching && 'opacity-50')}
    >
      {children(consulta.data)}
    </div>
  )
}

export default EstadoConsulta
