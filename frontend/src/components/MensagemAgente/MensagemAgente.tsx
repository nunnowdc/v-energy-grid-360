import { Waypoints } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import FeedbackResposta from '@/components/FeedbackResposta/FeedbackResposta'
import PassoAPasso from '@/components/PassoAPasso/PassoAPasso'
import SeloConfianca from '@/components/SeloConfianca/SeloConfianca'
import { Button } from '@/components/ui/button'
import type { RespostaAgente } from '@/hooks/use-agente-ia'
import { formatarNumero } from '@/lib/formatacao'

// Resposta do agente na conversa, com o selo de confiança, o tempo, o 👍/👎 e
// o passo a passo, que só abre (e só é buscado) quando a pessoa pede
function MensagemAgente({ resposta }: { resposta: RespostaAgente }) {
  const [verPassos, setVerPassos] = useState(false)
  const idPassos = useId()
  const passos = useRef<HTMLDivElement>(null)

  // O botão costuma estar no fim da conversa: rola para o passo a passo aparecer
  useEffect(() => {
    if (verPassos) {
      passos.current?.scrollIntoView?.({ behavior: 'smooth', block: 'nearest' })
    }
  }, [verPassos])

  return (
    <div className="flex min-w-0 flex-col gap-2 rounded-xl rounded-tl-sm border bg-card px-3.5 py-2.5">
      <p className="text-sm leading-relaxed break-words whitespace-pre-line">{resposta.answer}</p>
      {resposta.fontes.length > 0 && (
        <p className="text-xs text-muted-foreground">Fontes: {resposta.fontes.join(', ')}</p>
      )}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 border-t pt-2">
        <SeloConfianca selo={resposta.selo_confianca} />
        <span className="text-xs tabular-nums text-muted-foreground">
          {formatarNumero(resposta.tempo_ms / 1000)} s
        </span>
        <div className="ml-auto">
          <FeedbackResposta auditId={resposta.audit_id} />
        </div>
      </div>
      <Button
        variant={verPassos ? 'secondary' : 'outline'}
        size="xs"
        className="self-start"
        aria-expanded={verPassos}
        aria-controls={idPassos}
        onClick={() => setVerPassos((atual) => !atual)}
      >
        <Waypoints />
        {verPassos ? 'Esconder o passo a passo' : 'Ver o passo a passo'}
      </Button>
      {verPassos && (
        <div ref={passos} id={idPassos} className="scroll-mt-2 border-t pt-3">
          <PassoAPasso auditId={resposta.audit_id} />
        </div>
      )}
    </div>
  )
}

export default MensagemAgente
