import { CircleCheck, CircleDot } from 'lucide-react'
import Etiqueta from '@/components/Etiqueta/Etiqueta'
import { textoDoCodigo } from '@/config/codigos'

// A Gold marca o chamado como encerrado quando ele tem data de fechamento
const encerrado = (status: string) => ['ENCERRADO', 'FECHADO'].includes(status)

// Situação do chamado numa etiqueta: em aberto chama atenção, encerrado fica em verde
function StatusChamado({ status }: { status: string }) {
  return encerrado(status) ? (
    <Etiqueta tom="positivo" Icone={CircleCheck}>
      {textoDoCodigo(status)}
    </Etiqueta>
  ) : (
    <Etiqueta tom="atencao" Icone={CircleDot}>
      {textoDoCodigo(status)}
    </Etiqueta>
  )
}

export default StatusChamado
