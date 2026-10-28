import { LoaderCircle, RotateCw, TriangleAlert } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import MensagemAgente, { AvatarAgente } from '@/components/MensagemAgente/MensagemAgente'
import { Button } from '@/components/ui/button'
import type { RespostaAgente } from '@/hooks/use-agente-ia'

// Uma pergunta e o que veio dela. Sem resposta e sem erro, ainda está em andamento
export type Troca = {
  id: string
  pergunta: string
  resposta?: RespostaAgente
  erro?: string
}

type ConversaAgenteProps = {
  trocas: Troca[]
  // audit_id da resposta com o passo a passo aberto
  selecionada?: string
  aoVerPassos: (auditId: string) => void
  aoTentarDeNovo: (troca: Troca) => void
}

// O agente leva alguns segundos: o contador mostra que ele está trabalhando
function Aguardando() {
  const [segundos, setSegundos] = useState(0)

  useEffect(() => {
    const relogio = setInterval(() => setSegundos((atual) => atual + 1), 1000)
    return () => clearInterval(relogio)
  }, [])

  return (
    <div className="flex items-center gap-2 rounded-xl rounded-tl-sm border bg-card px-3.5 py-2.5 text-sm text-muted-foreground">
      <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
      Analisando a pergunta e consultando os dados
      <span className="tabular-nums">· {segundos} s</span>
    </div>
  )
}

function Falha({ mensagem, aoTentarDeNovo }: { mensagem: string; aoTentarDeNovo: () => void }) {
  return (
    <div className="flex flex-col items-start gap-2 rounded-xl rounded-tl-sm border border-destructive/30 bg-card px-3.5 py-2.5 text-sm">
      <p className="flex items-center gap-1.5 font-medium">
        <TriangleAlert aria-hidden="true" className="size-4 text-destructive" />
        Não foi possível obter a resposta
      </p>
      <p className="text-muted-foreground">{mensagem}</p>
      <Button variant="outline" size="sm" onClick={aoTentarDeNovo}>
        <RotateCw />
        Tentar de novo
      </Button>
    </div>
  )
}

// Perguntas à direita, respostas à esquerda; desce sozinha a cada mensagem nova
function ConversaAgente({ trocas, selecionada, aoVerPassos, aoTentarDeNovo }: ConversaAgenteProps) {
  const fim = useRef<HTMLDivElement>(null)
  const ultima = trocas.at(-1)

  useEffect(() => {
    fim.current?.scrollIntoView?.({ block: 'end' })
  }, [trocas.length, ultima?.resposta, ultima?.erro])

  return (
    <div role="log" aria-label="Conversa com o agente" className="flex flex-col gap-4">
      {trocas.map((troca) => (
        <div key={troca.id} className="flex flex-col gap-4">
          <p className="ml-auto max-w-[85%] rounded-xl rounded-tr-sm bg-primary px-3.5 py-2 text-sm break-words whitespace-pre-line text-primary-foreground">
            {troca.pergunta}
          </p>
          <div className="flex gap-2.5">
            <AvatarAgente />
            <div className="min-w-0 flex-1">
              {troca.resposta ? (
                <MensagemAgente
                  resposta={troca.resposta}
                  selecionada={troca.resposta.audit_id === selecionada}
                  aoVerPassos={() => aoVerPassos(troca.resposta!.audit_id)}
                />
              ) : troca.erro ? (
                <Falha mensagem={troca.erro} aoTentarDeNovo={() => aoTentarDeNovo(troca)} />
              ) : (
                <Aguardando />
              )}
            </div>
          </div>
        </div>
      ))}
      <div ref={fim} />
    </div>
  )
}

export default ConversaAgente
