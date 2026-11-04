import { CircleCheck, CircleX } from 'lucide-react'
import Etiqueta from '@/components/Etiqueta/Etiqueta'
import SeloConfianca from '@/components/SeloConfianca/SeloConfianca'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { CasoAvaliacao, TipoCaso } from '@/hooks/use-avaliacoes-agente'
import { formatarNumero, formatarSegundos } from '@/lib/formatacao'

// O que o caso espera do agente
const nomesTipos: Record<TipoCaso, string> = {
  sql: 'Consulta aos dados',
  rag: 'Documentos',
  recusa: 'Recusa',
}

// Os casos da última execução do golden set, com o motivo de cada resultado
function CasosAvaliacao({ casos }: { casos: CasoAvaliacao[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Caso</TableHead>
          <TableHead>Espera</TableHead>
          <TableHead>Pergunta</TableHead>
          <TableHead>Resultado</TableHead>
          <TableHead>Por quê</TableHead>
          <TableHead>Selo da resposta</TableHead>
          <TableHead className="text-right">Tokens</TableHead>
          <TableHead className="text-right">Tempo</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {casos.map((caso) => (
          <TableRow key={caso.caso_id}>
            <TableCell className="tabular-nums whitespace-nowrap">{caso.caso_id}</TableCell>
            <TableCell className="whitespace-nowrap">{nomesTipos[caso.tipo] ?? caso.tipo}</TableCell>
            <TableCell className="max-w-72 min-w-56 whitespace-normal">
              <span title={caso.pergunta} className="line-clamp-2">
                {caso.pergunta}
              </span>
            </TableCell>
            <TableCell>
              {caso.passou ? (
                <Etiqueta tom="positivo" Icone={CircleCheck}>
                  Passou
                </Etiqueta>
              ) : (
                <Etiqueta tom="negativo" Icone={CircleX}>
                  Falhou
                </Etiqueta>
              )}
            </TableCell>
            <TableCell className="max-w-72 min-w-48 whitespace-normal text-muted-foreground">
              <span title={caso.sql_gerado ?? undefined}>{caso.motivo}</span>
            </TableCell>
            <TableCell>
              <SeloConfianca selo={caso.selo} />
            </TableCell>
            <TableCell className="text-right tabular-nums">{formatarNumero(caso.tokens)}</TableCell>
            <TableCell className="text-right tabular-nums">{formatarSegundos(caso.tempo_ms)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

export default CasosAvaliacao
