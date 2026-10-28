import { LayoutDashboard, Waypoints } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router'
import FeedbackResposta from '@/components/FeedbackResposta/FeedbackResposta'
import PassoAPasso from '@/components/PassoAPasso/PassoAPasso'
import SeloConfianca from '@/components/SeloConfianca/SeloConfianca'
import TextoMarkdown from '@/components/TextoMarkdown/TextoMarkdown'
import { Button } from '@/components/ui/button'
import type { RespostaAgente } from '@/hooks/use-agente-ia'
import { formatarNumero } from '@/lib/formatacao'

// Tela que a resposta abriu no dashboard, ex.: "Receita · Recife"
export type TelaNoDashboard = { caminho: string; descricao: string }

type MensagemAgenteProps = {
  resposta: RespostaAgente
  tela?: TelaNoDashboard
}

// Resposta do agente na conversa, com o selo de confiança, o tempo, o 👍/👎,
// a tela que ela abriu no dashboard e o passo a passo, que só abre (e só é
// buscado) quando a pessoa pede
function MensagemAgente({ resposta, tela }: MensagemAgenteProps) {
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
      <TextoMarkdown texto={resposta.answer} />
      {resposta.fontes.length > 0 && (
        <p className="text-xs text-muted-foreground">Fontes: {resposta.fontes.join(', ')}</p>
      )}
      {/* O dashboard já foi para essa tela; o link reabre se a pessoa sair dela */}
      {tela && (
        <Link
          to={tela.caminho}
          className="inline-flex items-center gap-1.5 self-start text-xs font-medium text-primary hover:underline"
        >
          <LayoutDashboard aria-hidden="true" className="size-3.5" />
          No dashboard: {tela.descricao}
        </Link>
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
