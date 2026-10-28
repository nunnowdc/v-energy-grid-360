import { Link } from 'react-router'
import StatusOrdem from '@/components/StatusOrdem/StatusOrdem'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  useCancelarOrdem,
  useMudarOrdem,
  type OrdemInspecao,
  type ResultadoInspecao,
} from '@/hooks/use-ordens-inspecao'
import { ErroApi } from '@/lib/api/erro-api'
import { formatarInstante } from '@/lib/formatacao'

const textoResultado: Record<ResultadoInspecao, string> = {
  IRREGULARIDADE_CONFIRMADA: 'Irregularidade confirmada',
  SEM_IRREGULARIDADE: 'Sem irregularidade',
}

// Os botões só oferecem mudanças que valem para a situação da ordem: o 409 quer
// dizer que outra pessoa mudou a ordem antes (a lista já foi recarregada)
function textoErro(erro: Error) {
  if (erro instanceof ErroApi && erro.status === 409) {
    return 'Essa ordem já tinha mudado de situação. A lista foi atualizada.'
  }
  return erro instanceof ErroApi ? erro.message : 'Não foi possível atualizar a ordem. Tente de novo.'
}

type OrdensInspecaoProps = {
  ordens: OrdemInspecao[]
}

// Ordens geradas a partir da fila. Cada uma anda: aberta → em campo → concluída
// (com o resultado da inspeção). Até concluir, dá para cancelar
function OrdensInspecao({ ordens }: OrdensInspecaoProps) {
  const mudar = useMudarOrdem()
  const cancelar = useCancelarOrdem()
  const ocupado = mudar.isPending || cancelar.isPending
  const erro = mudar.error ?? cancelar.error

  return (
    <div className="flex flex-col gap-3">
      {erro && (
        <p role="alert" className="text-sm text-destructive">
          {textoErro(erro)}
        </p>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Ordem</TableHead>
            <TableHead>UC</TableHead>
            <TableHead>Bairro · município</TableHead>
            <TableHead>Gerada em</TableHead>
            <TableHead>Situação</TableHead>
            <TableHead className="text-right">Ações</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {ordens.map((ordem) => (
            <TableRow key={ordem.id_ordem}>
              <TableCell className="tabular-nums">{ordem.id_ordem}</TableCell>
              <TableCell>
                <Link to={`/visao-360/${ordem.id_uc}`} className="tabular-nums text-primary hover:underline">
                  {ordem.id_uc}
                </Link>
              </TableCell>
              <TableCell className="whitespace-nowrap">
                {ordem.bairro} <span className="text-muted-foreground">· {ordem.municipio}</span>
              </TableCell>
              <TableCell>{formatarInstante(ordem.criada_em)}</TableCell>
              <TableCell>
                <StatusOrdem status={ordem.status} />
                {ordem.resultado && (
                  <span className="block text-xs text-muted-foreground">{textoResultado[ordem.resultado]}</span>
                )}
              </TableCell>
              <TableCell>
                <div className="flex flex-wrap justify-end gap-1.5">
                  {ordem.status === 'ABERTA' && (
                    <Button
                      size="sm"
                      disabled={ocupado}
                      onClick={() => mudar.mutate({ idOrdem: ordem.id_ordem, mudanca: { status: 'EM_CAMPO' } })}
                    >
                      Enviar para campo
                    </Button>
                  )}
                  {ordem.status === 'EM_CAMPO' &&
                    (Object.keys(textoResultado) as ResultadoInspecao[]).map((resultado) => (
                      <Button
                        key={resultado}
                        size="sm"
                        variant="outline"
                        disabled={ocupado}
                        onClick={() =>
                          mudar.mutate({ idOrdem: ordem.id_ordem, mudanca: { status: 'CONCLUIDA', resultado } })
                        }
                      >
                        {textoResultado[resultado]}
                      </Button>
                    ))}
                  {(ordem.status === 'ABERTA' || ordem.status === 'EM_CAMPO') && (
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={ocupado}
                      onClick={() => cancelar.mutate(ordem.id_ordem)}
                    >
                      Cancelar
                    </Button>
                  )}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

export default OrdensInspecao
