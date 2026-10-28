import { ThumbsDown, ThumbsUp } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { useFeedbackAgente } from '@/hooks/use-agente-ia'

// 👍/👎 de uma resposta, gravado na auditoria para medir a acurácia do agente.
// Depois de registrado, o voto fica fixo
function FeedbackResposta({ auditId }: { auditId: string }) {
  const [voto, setVoto] = useState<boolean>()
  const feedback = useFeedbackAgente()
  const registrado = feedback.isSuccess

  function votar(util: boolean) {
    setVoto(util)
    feedback.mutate({ auditId, util })
  }

  return (
    <div className="flex items-center gap-1">
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="Resposta útil"
        aria-pressed={voto === true}
        disabled={registrado || feedback.isPending}
        className={voto === true ? 'text-primary' : 'text-muted-foreground'}
        onClick={() => votar(true)}
      >
        <ThumbsUp />
      </Button>
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="Resposta não ajudou"
        aria-pressed={voto === false}
        disabled={registrado || feedback.isPending}
        className={voto === false ? 'text-primary' : 'text-muted-foreground'}
        onClick={() => votar(false)}
      >
        <ThumbsDown />
      </Button>
      <span role="status" className="text-xs text-muted-foreground">
        {registrado && 'Obrigado pelo retorno'}
        {feedback.isError && 'Não foi possível registrar. Tente de novo.'}
      </span>
    </div>
  )
}

export default FeedbackResposta
