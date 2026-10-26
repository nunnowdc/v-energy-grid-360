import type { ReactNode } from 'react'
import EstadoConsulta, { type EstadoConsultaProps } from '@/components/EstadoConsulta/EstadoConsulta'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

type BlocoDadosProps<T> = EstadoConsultaProps<T> & {
  titulo: string
  descricao?: string
  // Ex.: botão de exportar, no canto do título
  acao?: ReactNode
  className?: string
}

// Cartão com título que mostra os 4 estados de uma consulta (gráficos, tabelas)
function BlocoDados<T>({ titulo, descricao, acao, className, ...estado }: BlocoDadosProps<T>) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-[15px] font-semibold">{titulo}</CardTitle>
        {descricao && <CardDescription>{descricao}</CardDescription>}
        {acao && <CardAction>{acao}</CardAction>}
      </CardHeader>
      <CardContent>
        <EstadoConsulta {...estado} />
      </CardContent>
    </Card>
  )
}

export default BlocoDados
