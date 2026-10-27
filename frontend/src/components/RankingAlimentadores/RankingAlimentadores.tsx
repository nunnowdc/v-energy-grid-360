import { ChevronRight, TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import Variacao from '@/components/Variacao/Variacao'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { AlimentadorContinuidade } from '@/hooks/use-continuidade'
import { variacaoPercentual } from '@/lib/comparacao'
import { formatarNumero } from '@/lib/formatacao'

// Quantos aparecem antes de "Mostrar todos"
const PRIMEIROS = 10

type RankingAlimentadoresProps = {
  ranking: AlimentadorContinuidade[]
  // Alimentador já escolhido no filtro (a linha fica marcada e não é clicável)
  escolhido?: string
  aoEscolher: (alimentador: string) => void
}

// Piores alimentadores em DEC: onde a manutenção preventiva rende mais.
// Clicar no código filtra a tela por ele
function RankingAlimentadores({ ranking, escolhido, aoEscolher }: RankingAlimentadoresProps) {
  const [todos, setTodos] = useState(false)
  const visiveis = todos ? ranking : ranking.slice(0, PRIMEIROS)

  return (
    <div className="flex flex-col gap-2">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="text-right">#</TableHead>
            <TableHead>Alimentador</TableHead>
            <TableHead>Município principal</TableHead>
            <TableHead className="text-right">UCs</TableHead>
            <TableHead className="text-right">DEC (h)</TableHead>
            <TableHead className="text-right">FEC</TableHead>
            <TableHead className="text-right">DEC sem dias críticos</TableHead>
            <TableHead className="text-right">DEC vs. período anterior</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {visiveis.map((linha, indice) => {
            const variacao = variacaoPercentual(linha.dec, linha.dec_anterior)
            return (
              <TableRow
                key={linha.alimentador}
                data-state={linha.alimentador === escolhido ? 'selected' : undefined}
              >
                <TableCell className="text-right font-mono text-muted-foreground">{indice + 1}</TableCell>
                <TableCell>
                  {linha.alimentador === escolhido ? (
                    <span className="font-mono font-semibold">{linha.alimentador}</span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => aoEscolher(linha.alimentador)}
                      className="inline-flex cursor-pointer items-center gap-0.5 font-mono text-primary hover:underline"
                    >
                      {linha.alimentador}
                      <ChevronRight aria-hidden="true" className="size-3.5" />
                    </button>
                  )}
                </TableCell>
                <TableCell>{linha.municipio_principal}</TableCell>
                <TableCell className="text-right font-mono">
                  {linha.alimentador_pequeno && (
                    <span className="mr-1.5 inline-flex items-center gap-1 font-sans text-xs text-muted-foreground">
                      <TriangleAlert aria-hidden="true" className="size-3.5" />
                      Menos de 100 UCs
                    </span>
                  )}
                  {formatarNumero(linha.total_ucs)}
                </TableCell>
                <TableCell className="text-right font-mono font-semibold">{formatarNumero(linha.dec)}</TableCell>
                <TableCell className="text-right font-mono">{formatarNumero(linha.fec)}</TableCell>
                <TableCell className="text-right font-mono text-muted-foreground">
                  {formatarNumero(linha.dec_sem_dia_critico)}
                </TableCell>
                <TableCell className="text-right">
                  {variacao === undefined ? '—' : <Variacao percentual={variacao} />}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
      {ranking.length > PRIMEIROS && (
        <Button variant="ghost" size="sm" className="self-start" onClick={() => setTodos((atual) => !atual)}>
          {todos ? `Mostrar só os ${PRIMEIROS} piores` : `Mostrar todos os ${ranking.length} alimentadores`}
        </Button>
      )}
    </div>
  )
}

export default RankingAlimentadores
