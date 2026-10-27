import { Link } from 'react-router'
import StatusOrdem from '@/components/StatusOrdem/StatusOrdem'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { lerMotivos } from '@/config/motivos'
import type { ItemFila } from '@/hooks/use-fila-inspecao'
import { formatarEnergia } from '@/lib/formatacao'

type FilaSuspeitasProps = {
  itens: ItemFila[]
  selecionadas: Set<string>
  aoMarcar: (idUc: string, marcada: boolean) => void
}

function Motivos({ motivoSuspeita }: { motivoSuspeita: string }) {
  return (
    <ul className="flex flex-wrap gap-1">
      {lerMotivos(motivoSuspeita).map(({ texto, pontos }) => (
        <li key={texto} className="rounded-md border bg-muted/50 px-1.5 py-0.5 text-xs whitespace-nowrap">
          {texto}
          {pontos !== undefined && (
            <span className="ml-1 font-mono text-muted-foreground">
              {pontos > 0 ? '+' : ''}
              {pontos}
            </span>
          )}
        </li>
      ))}
    </ul>
  )
}

function Score({ valor }: { valor: number }) {
  return (
    <div className="flex items-center justify-end gap-2">
      <div aria-hidden="true" className="h-2 w-16 rounded-r-[4px] bg-muted">
        <div className="h-full rounded-r-[4px] bg-primary" style={{ width: `${valor}%` }} />
      </div>
      <span className="w-7 text-right font-mono font-semibold">{valor}</span>
    </div>
  )
}

// Fila de UCs suspeitas na prioridade da Gold. A UC que já tem ordem aberta
// mostra a situação da ordem no lugar da caixa de seleção
function FilaSuspeitas({ itens, selecionadas, aoMarcar }: FilaSuspeitasProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-24">Ordem</TableHead>
          <TableHead className="text-right">#</TableHead>
          <TableHead>UC</TableHead>
          <TableHead>Bairro · município</TableHead>
          <TableHead>Motivos da suspeita</TableHead>
          <TableHead className="text-right">Energia a recuperar</TableHead>
          <TableHead className="text-right">Score</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {itens.map((item) => (
          <TableRow key={item.id_uc} data-state={selecionadas.has(item.id_uc) ? 'selected' : undefined}>
            <TableCell>
              {item.ordem_aberta ? (
                <StatusOrdem status={item.ordem_aberta.status} />
              ) : (
                <label className="flex cursor-pointer items-center gap-2 text-xs text-muted-foreground">
                  <input
                    type="checkbox"
                    className="size-4 cursor-pointer accent-primary"
                    checked={selecionadas.has(item.id_uc)}
                    onChange={(evento) => aoMarcar(item.id_uc, evento.target.checked)}
                    aria-label={`Selecionar ${item.id_uc}`}
                  />
                  Gerar
                </label>
              )}
            </TableCell>
            <TableCell className="text-right font-mono text-muted-foreground">{item.prioridade}</TableCell>
            <TableCell>
              <Link to={`/visao-360/${item.id_uc}`} className="font-mono text-primary hover:underline">
                {item.id_uc}
              </Link>
            </TableCell>
            <TableCell className="whitespace-nowrap">
              {item.bairro} <span className="text-muted-foreground">· {item.municipio}</span>
            </TableCell>
            <TableCell className="min-w-64 whitespace-normal">
              <Motivos motivoSuspeita={item.motivo_suspeita} />
            </TableCell>
            <TableCell className="text-right font-mono whitespace-nowrap">
              {item.kwh_recuperavel_estimado_ano === 0 ? (
                <span className="text-muted-foreground">—</span>
              ) : (
                `${formatarEnergia(item.kwh_recuperavel_estimado_ano)}/ano`
              )}
            </TableCell>
            <TableCell>
              <Score valor={item.score} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

export default FilaSuspeitas
