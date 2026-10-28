import { SendHorizontal } from 'lucide-react'
import { useState, type FormEvent, type KeyboardEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

// Mesmo limite do filtro de segurança do agente (MAX_COMPRIMENTO)
const LIMITE_CARACTERES = 1200

type CaixaPerguntaProps = {
  aoEnviar: (pergunta: string) => void
  // Enquanto o agente responde, dá para escrever mas não enviar
  aguardando: boolean
}

// Enter envia; Shift+Enter quebra a linha
function CaixaPergunta({ aoEnviar, aguardando }: CaixaPerguntaProps) {
  const [texto, setTexto] = useState('')
  const pergunta = texto.trim()
  const podeEnviar = pergunta !== '' && !aguardando

  function enviar(evento?: FormEvent) {
    evento?.preventDefault()
    if (!podeEnviar) {
      return
    }
    aoEnviar(pergunta)
    setTexto('')
  }

  function aoTeclar(evento: KeyboardEvent<HTMLTextAreaElement>) {
    if (evento.key === 'Enter' && !evento.shiftKey && !evento.nativeEvent.isComposing) {
      evento.preventDefault()
      enviar()
    }
  }

  return (
    <form onSubmit={enviar} className="flex items-end gap-2">
      <label htmlFor="pergunta-agente" className="sr-only">
        Sua pergunta
      </label>
      <Textarea
        id="pergunta-agente"
        value={texto}
        onChange={(evento) => setTexto(evento.target.value)}
        onKeyDown={aoTeclar}
        maxLength={LIMITE_CARACTERES}
        rows={1}
        placeholder="Pergunte sobre receita, consumo, continuidade…"
        className="max-h-40 min-h-10 resize-none bg-card"
      />
      <Button type="submit" size="icon-lg" disabled={!podeEnviar} aria-label="Enviar pergunta">
        <SendHorizontal />
      </Button>
    </form>
  )
}

export default CaixaPergunta
