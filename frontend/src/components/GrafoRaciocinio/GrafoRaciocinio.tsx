import { CircleCheck, CircleSlash, RotateCcw, TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'
import { nosAgente } from '@/config/nos-agente'
import type { PassoAgente, SituacaoPasso } from '@/lib/passos-agente'
import { cn } from '@/lib/utils'

const aparencia: Record<SituacaoPasso, { texto: string; Icone: typeof CircleCheck; no: string; rotulo: string }> = {
  concluido: {
    texto: 'Concluído',
    Icone: CircleCheck,
    no: 'border-primary bg-primary text-primary-foreground',
    rotulo: 'text-primary',
  },
  atencao: {
    texto: 'Atenção',
    Icone: TriangleAlert,
    no: 'border-amber-500 bg-card text-amber-700',
    rotulo: 'text-amber-700',
  },
  interrompido: {
    texto: 'Interrompido',
    Icone: CircleSlash,
    no: 'border-destructive bg-card text-destructive',
    rotulo: 'text-destructive',
  },
}

type GrafoRaciocinioProps = {
  passos: PassoAgente[]
  // Conteúdo a mais no último passo de um nó (ex.: a consulta no nó 7)
  extras?: Partial<Record<number, ReactNode>>
}

// Caminho que o agente percorreu no grafo dele: cada nó é um passo, ligado
// ao seguinte, com o que o agente registrou ao passar por ali
function GrafoRaciocinio({ passos, extras = {} }: GrafoRaciocinioProps) {
  const ultimoDoNo = new Map(passos.map((passo, indice) => [passo.no, indice]))

  return (
    <ol aria-label="Passos do agente" className="flex flex-col">
      {passos.map((passo, indice) => {
        const { nome, funcao } = (passo.no !== null && nosAgente[passo.no]) || {
          nome: 'Passo fora do padrão',
          funcao: 'O agente registrou um passo que o portal não reconhece',
        }
        const { texto, Icone, no, rotulo } = aparencia[passo.situacao]
        const extra = passo.no !== null && ultimoDoNo.get(passo.no) === indice ? extras[passo.no] : undefined

        return (
          <li key={indice} className="relative flex gap-3 pb-5 last:pb-0">
            {/* Aresta até o próximo nó */}
            {indice < passos.length - 1 && (
              <span aria-hidden="true" className="absolute top-8 bottom-0 left-4 w-0.5 -translate-x-1/2 bg-border" />
            )}
            <span
              aria-hidden="true"
              className={cn(
                'relative flex size-8 shrink-0 items-center justify-center rounded-full border-2 text-xs font-semibold tabular-nums',
                no,
              )}
            >
              {passo.no ?? '?'}
            </span>

            <div className="flex min-w-0 flex-1 flex-col gap-1 pt-1">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                <p className="text-sm font-semibold">
                  <span className="sr-only">Nó {passo.no ?? 'sem número'}: </span>
                  {nome}
                </p>
                <span className={cn('inline-flex items-center gap-1 text-xs font-medium', rotulo)}>
                  <Icone aria-hidden="true" className="size-3.5" />
                  {texto}
                </span>
                {passo.repeticao && (
                  <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                    <RotateCcw aria-hidden="true" className="size-3.5" />
                    Nova tentativa
                  </span>
                )}
              </div>
              <p className="text-xs text-muted-foreground">{funcao}</p>
              <ul className="mt-0.5 flex flex-col gap-1 rounded-md bg-muted/50 px-2.5 py-1.5 text-[13px] break-words">
                {passo.detalhes.map((detalhe, posicao) => (
                  <li key={posicao}>{detalhe}</li>
                ))}
              </ul>
              {extra}
            </div>
          </li>
        )
      })}
    </ol>
  )
}

export default GrafoRaciocinio
