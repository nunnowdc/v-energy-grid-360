import { ThumbsDown, ThumbsUp, Waypoints } from 'lucide-react'
import { useState } from 'react'
import PassoAPasso from '@/components/PassoAPasso/PassoAPasso'
import SeloConfianca from '@/components/SeloConfianca/SeloConfianca'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { nomesPerfis } from '@/config/perfis'
import type { PerguntaAuditada } from '@/hooks/use-uso-agente'
import { formatarInstante, formatarNumero, formatarSegundos } from '@/lib/formatacao'

// Avaliação de quem perguntou, sempre com ícone e texto
function Avaliacao({ valor }: { valor: PerguntaAuditada['avaliacao'] }) {
  if (valor === 1) {
    return (
      <span className="inline-flex items-center gap-1 text-positivo">
        <ThumbsUp aria-hidden="true" className="size-3.5" />
        Útil
      </span>
    )
  }
  if (valor === -1) {
    return (
      <span className="inline-flex items-center gap-1 text-negativo">
        <ThumbsDown aria-hidden="true" className="size-3.5" />
        Não útil
      </span>
    )
  }
  return <span className="text-muted-foreground">—</span>
}

// As perguntas mais recentes, com o passo a passo de cada uma num painel ao lado
function UltimasPerguntas({ perguntas }: { perguntas: PerguntaAuditada[] }) {
  // A pergunta continua escolhida enquanto o painel fecha, para o conteúdo não sumir na animação
  const [escolhida, setEscolhida] = useState<PerguntaAuditada | null>(null)
  const [aberto, setAberto] = useState(false)

  const abrir = (pergunta: PerguntaAuditada) => {
    setEscolhida(pergunta)
    setAberto(true)
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Quando</TableHead>
            <TableHead>Pergunta</TableHead>
            <TableHead>Perfil</TableHead>
            <TableHead>Resultado</TableHead>
            <TableHead className="text-right">Tempo</TableHead>
            <TableHead className="text-right">Tokens</TableHead>
            <TableHead>Avaliação</TableHead>
            <TableHead className="text-right">
              <span className="sr-only">Ações</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {perguntas.map((pergunta) => (
            <TableRow key={pergunta.id}>
              <TableCell className="tabular-nums whitespace-nowrap">{formatarInstante(pergunta.data_hora)}</TableCell>
              <TableCell className="max-w-80 min-w-56 whitespace-normal">
                <span title={pergunta.pergunta} className="line-clamp-2">
                  {pergunta.pergunta}
                </span>
              </TableCell>
              <TableCell className="whitespace-nowrap">
                {pergunta.perfil ? (
                  nomesPerfis[pergunta.perfil] ?? pergunta.perfil
                ) : (
                  <span title="Pergunta de antes do login" className="text-muted-foreground">
                    —
                  </span>
                )}
              </TableCell>
              <TableCell>
                <SeloConfianca selo={pergunta.selo} />
              </TableCell>
              <TableCell className="text-right tabular-nums">{formatarSegundos(pergunta.tempo_ms)}</TableCell>
              <TableCell className="text-right tabular-nums">{formatarNumero(pergunta.tokens)}</TableCell>
              <TableCell className="whitespace-nowrap">
                <Avaliacao valor={pergunta.avaliacao} />
              </TableCell>
              <TableCell className="text-right">
                <Button variant="outline" size="xs" onClick={() => abrir(pergunta)}>
                  <Waypoints />
                  Passo a passo
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Sheet open={aberto} onOpenChange={setAberto}>
        <SheetContent className="w-full overflow-y-auto data-[side=right]:sm:max-w-xl">
          <SheetHeader>
            <SheetTitle>Como o agente chegou na resposta</SheetTitle>
            <SheetDescription>{escolhida?.pergunta}</SheetDescription>
          </SheetHeader>
          <div className="px-4 pb-4">{escolhida && <PassoAPasso auditId={escolhida.id} />}</div>
        </SheetContent>
      </Sheet>
    </>
  )
}

export default UltimasPerguntas
