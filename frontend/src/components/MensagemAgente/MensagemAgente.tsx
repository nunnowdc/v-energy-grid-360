import { Sparkles, Waypoints } from 'lucide-react'
import FeedbackResposta from '@/components/FeedbackResposta/FeedbackResposta'
import SeloConfianca from '@/components/SeloConfianca/SeloConfianca'
import { Button } from '@/components/ui/button'
import type { RespostaAgente } from '@/hooks/use-agente-ia'
import { formatarNumero } from '@/lib/formatacao'
import { cn } from '@/lib/utils'

type MensagemAgenteProps = {
  resposta: RespostaAgente
  // A resposta cujo passo a passo está aberto no painel
  selecionada: boolean
  aoVerPassos: () => void
}

// Resposta do agente na conversa, com o selo de confiança, o tempo, o acesso
// ao passo a passo e o 👍/👎
function MensagemAgente({ resposta, selecionada, aoVerPassos }: MensagemAgenteProps) {
  return (
    <div
      className={cn(
        'flex min-w-0 flex-col gap-2 rounded-xl rounded-tl-sm border bg-card px-3.5 py-2.5 transition-shadow',
        selecionada && 'ring-2 ring-primary/30',
      )}
    >
      <p className="text-sm leading-relaxed break-words whitespace-pre-line">{resposta.answer}</p>
      {resposta.fontes.length > 0 && (
        <p className="text-xs text-muted-foreground">Fontes: {resposta.fontes.join(', ')}</p>
      )}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 border-t pt-2">
        <SeloConfianca selo={resposta.selo_confianca} />
        <span className="text-xs tabular-nums text-muted-foreground">
          {formatarNumero(resposta.tempo_ms / 1000)} s
        </span>
        <Button
          variant={selecionada ? 'secondary' : 'outline'}
          size="xs"
          aria-pressed={selecionada}
          onClick={aoVerPassos}
        >
          <Waypoints />
          Ver o passo a passo
        </Button>
        <div className="ml-auto">
          <FeedbackResposta auditId={resposta.audit_id} />
        </div>
      </div>
    </div>
  )
}

// Ícone que marca as falas do agente
export function AvatarAgente() {
  return (
    <span
      aria-hidden="true"
      className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary"
    >
      <Sparkles className="size-4" />
    </span>
  )
}

export default MensagemAgente
