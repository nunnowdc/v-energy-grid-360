import { ChevronRight, RotateCcw, TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import Variacao from '@/components/Variacao/Variacao'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { AlimentadorContinuidade } from '@/hooks/use-continuidade'
import { variacaoPercentual } from '@/lib/comparacao'
import { formatarNumero } from '@/lib/formatacao'

// Quantos aparecem antes de "Mostrar todos"
const PRIMEIROS = 10

// Horas sem energia somando todos os clientes do alimentador. O DEC é a média por UC
// e o total de UCs não muda no período, então DEC × UCs dá a soma exata
const horasSemEnergia = (linha: AlimentadorContinuidade) => linha.dec * linha.total_ucs

const horas = (valor: number) => `${formatarNumero(valor)} h`

const ordens = [
  // Onde a manutenção alcança mais clientes: um alimentador pequeno não passa na frente de um grande
  { valor: 'horas', rotulo: 'Mais horas sem energia', valorDe: horasSemEnergia },
  // A média por cliente, que é o indicador cobrado pela ANEEL
  { valor: 'dec', rotulo: 'Maior DEC', valorDe: (linha: AlimentadorContinuidade) => linha.dec },
] as const

type Ordem = (typeof ordens)[number]['valor']

type RankingAlimentadoresProps = {
  ranking: AlimentadorContinuidade[]
  // Alimentador já escolhido no filtro (a linha fica marcada e não é clicável)
  escolhido?: string
  aoEscolher: (alimentador: string) => void
  // Tira o alimentador do filtro e volta ao ranking completo
  aoVerTodos: () => void
}

// Piores alimentadores, por horas sem energia (padrão) ou por DEC.
// Clicar no código filtra a tela por ele; com um escolhido, a tabela tem uma linha só
// e o botão embaixo volta para todos, sem subir até os filtros
function RankingAlimentadores({ ranking, escolhido, aoEscolher, aoVerTodos }: RankingAlimentadoresProps) {
  const [todos, setTodos] = useState(false)
  const [ordem, setOrdem] = useState<Ordem>('horas')
  const { valorDe } = ordens.find((opcao) => opcao.valor === ordem)!
  const ordenado = [...ranking].sort(
    (a, b) => valorDe(b) - valorDe(a) || a.alimentador.localeCompare(b.alimentador),
  )
  const visiveis = todos ? ordenado : ordenado.slice(0, PRIMEIROS)

  return (
    <div className="flex flex-col gap-2">
      {ranking.length > 1 && (
        <div
          role="group"
          aria-label="Ordenar por"
          className="inline-flex h-9 items-center gap-0.5 self-start rounded-md border bg-card p-0.5"
        >
          {ordens.map((opcao) => (
            <Button
              key={opcao.valor}
              type="button"
              size="sm"
              variant={opcao.valor === ordem ? 'secondary' : 'ghost'}
              aria-pressed={opcao.valor === ordem}
              className="h-7 px-3 text-[13px]"
              onClick={() => setOrdem(opcao.valor)}
            >
              {opcao.rotulo}
            </Button>
          ))}
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="text-right">#</TableHead>
            {/* Só a largura do conteúdo: a sobra da tabela vai para as colunas de números */}
            <TableHead className="w-px">Alimentador</TableHead>
            <TableHead className="text-right">Horas sem energia</TableHead>
            <TableHead className="text-right">DEC (h)</TableHead>
            <TableHead className="text-right">FEC</TableHead>
            {/* Os títulos longos só quebram a linha quando falta espaço, para a tabela não rolar para o lado */}
            <TableHead className="whitespace-normal text-right">DEC sem dias críticos</TableHead>
            <TableHead className="text-right">DEC evitável</TableHead>
            <TableHead className="whitespace-normal text-right">DEC vs. período anterior</TableHead>
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
                <TableCell className="text-right tabular-nums text-muted-foreground">{indice + 1}</TableCell>
                {/* Código, município e o aviso de alimentador pequeno empilhados numa coluna só */}
                <TableCell>
                  <div className="flex flex-col gap-0.5">
                    {linha.alimentador === escolhido ? (
                      <span className="tabular-nums font-semibold">{linha.alimentador}</span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => aoEscolher(linha.alimentador)}
                        className="inline-flex cursor-pointer items-center gap-0.5 self-start tabular-nums text-primary hover:underline"
                      >
                        {linha.alimentador}
                        <ChevronRight aria-hidden="true" className="size-3.5" />
                      </button>
                    )}
                    <span className="text-xs text-muted-foreground">{linha.municipio_principal}</span>
                    {linha.alimentador_pequeno && (
                      <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                        <TriangleAlert aria-hidden="true" className="size-3.5" />
                        Menos de 100 UCs
                      </span>
                    )}
                  </div>
                </TableCell>
                {/* A conta fica apagada antes do resultado: UCs × DEC (o DEC arredondado, então a
                    multiplicação de cabeça dá perto, não igual) */}
                <TableCell className="text-right tabular-nums">
                  <span className="mr-2 text-xs text-muted-foreground">
                    {formatarNumero(linha.total_ucs)} UCs × {horas(linha.dec)}
                  </span>
                  <span className={ordem === 'horas' ? 'font-semibold' : undefined}>
                    {formatarNumero(Math.round(horasSemEnergia(linha)))}
                  </span>
                </TableCell>
                <TableCell className={`text-right tabular-nums ${ordem === 'dec' ? 'font-semibold' : ''}`}>
                  {formatarNumero(linha.dec)}
                </TableCell>
                <TableCell className="text-right tabular-nums">{formatarNumero(linha.fec)}</TableCell>
                <TableCell className="text-right tabular-nums text-muted-foreground">
                  {formatarNumero(linha.dec_sem_dia_critico)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatarNumero(linha.dec_evitavel)}
                  {linha.dec > 0 && (
                    <span className="ml-1.5 text-xs text-muted-foreground">
                      {formatarNumero((linha.dec_evitavel / linha.dec) * 100)}%
                    </span>
                  )}
                </TableCell>
                <TableCell className="text-right">
                  {variacao === undefined ? '—' : <Variacao percentual={variacao} sentido="subir-e-ruim" />}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
      {escolhido && (
        <Button variant="ghost" size="sm" className="self-start" onClick={aoVerTodos}>
          <RotateCcw />
          Ver todos os alimentadores
        </Button>
      )}
      {ranking.length > PRIMEIROS && (
        <Button variant="ghost" size="sm" className="self-start" onClick={() => setTodos((atual) => !atual)}>
          {todos ? `Mostrar só os ${PRIMEIROS} piores` : `Mostrar todos os ${ranking.length} alimentadores`}
        </Button>
      )}
    </div>
  )
}

export default RankingAlimentadores
