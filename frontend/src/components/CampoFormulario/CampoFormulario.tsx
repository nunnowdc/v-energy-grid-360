import { useId, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

// Atributos que ligam o controle ao rótulo e à mensagem abaixo dele
export type AtributosCampo = {
  id: string
  'aria-invalid'?: true
  'aria-describedby'?: string
}

type CampoFormularioProps = {
  rotulo: string
  // Mensagem de erro do campo; quando existe, aparece no lugar da dica
  erro?: string
  dica?: string
  children: (atributos: AtributosCampo) => ReactNode
}

// Rótulo, controle e uma linha de dica ou erro. O controle recebe os atributos
// pelo children, ex.: {(atributos) => <Input {...atributos} />}
function CampoFormulario({ rotulo, erro, dica, children }: CampoFormularioProps) {
  const id = useId()
  const idMensagem = useId()
  const mensagem = erro ?? dica

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {rotulo}
      </label>
      {children({
        id,
        'aria-invalid': erro ? true : undefined,
        'aria-describedby': mensagem ? idMensagem : undefined,
      })}
      {mensagem && (
        <p id={idMensagem} className={cn('text-xs', erro ? 'text-destructive' : 'text-muted-foreground')}>
          {mensagem}
        </p>
      )}
    </div>
  )
}

export default CampoFormulario
