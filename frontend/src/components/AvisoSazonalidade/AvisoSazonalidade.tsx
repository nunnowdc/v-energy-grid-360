import Nota from '@/components/Nota/Nota'
import { mesmosMesesDoAno } from '@/lib/periodos'

type Intervalo = { inicio: string; fim: string }

type AvisoSazonalidadeProps = {
  // Os dois períodos como vêm da API (yyyy-MM)
  base: Intervalo
  comparado: Intervalo
}

// Avisa quando os dois períodos cobrem meses diferentes do ano (ex.: jan–mar × jul–set):
// consumo e chuvas mudam ao longo do ano, então parte da variação é da estação
function AvisoSazonalidade({ base, comparado }: AvisoSazonalidadeProps) {
  if (mesmosMesesDoAno({ de: base.inicio, ate: base.fim }, { de: comparado.inicio, ate: comparado.fim })) {
    return null
  }
  return (
    <Nota tom="atencao" titulo="Meses diferentes do ano">
      Parte da variação pode ser da estação (consumo e chuvas mudam ao longo do ano), não uma mudança real.
    </Nota>
  )
}

export default AvisoSazonalidade
