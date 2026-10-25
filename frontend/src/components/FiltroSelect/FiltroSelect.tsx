import { useId } from 'react'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'

export type OpcaoFiltro = {
  valor: string
  rotulo: string
}

type FiltroSelectProps = {
  rotulo: string
  valor?: string
  opcoes: OpcaoFiltro[]
  // Texto da opção vazia, que significa "sem filtro" (ex.: "Todos")
  textoVazio: string
  desabilitado?: boolean
  aoMudar: (valor?: string) => void
}

function FiltroSelect({ rotulo, valor, opcoes, textoVazio, desabilitado, aoMudar }: FiltroSelectProps) {
  const id = useId()

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs font-medium text-muted-foreground">
        {rotulo}
      </label>
      <NativeSelect
        id={id}
        className="w-full sm:w-48"
        value={valor ?? ''}
        disabled={desabilitado}
        onChange={(evento) => aoMudar(evento.target.value || undefined)}
      >
        <NativeSelectOption value="">{textoVazio}</NativeSelectOption>
        {opcoes.map((opcao) => (
          <NativeSelectOption key={opcao.valor} value={opcao.valor}>
            {opcao.rotulo}
          </NativeSelectOption>
        ))}
      </NativeSelect>
    </div>
  )
}

export default FiltroSelect
