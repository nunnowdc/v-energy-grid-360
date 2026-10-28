import type { ReactNode } from 'react'
import Variacao from '@/components/Variacao/Variacao'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { DecomposicaoCompleta } from '@/hooks/use-receita'
import { variacaoPercentual } from '@/lib/comparacao'
import { formatarMoedaCompacta, formatarMoedaCompactaComSinal } from '@/lib/formatacao'

type LinhaDecomposicao = {
  chave: string
  rotulo: ReactNode
  dados: DecomposicaoCompleta
}

type TabelaDecomposicaoProps = {
  // Título da primeira coluna, ex.: "Município"
  colunaRotulo: string
  linhas: LinhaDecomposicao[]
}

const numero = 'text-right tabular-nums'

function variacaoOuTraco(atual: number, anterior: number) {
  const variacao = variacaoPercentual(atual, anterior)
  return variacao === undefined ? <span className="text-muted-foreground">—</span> : <Variacao percentual={variacao} />
}

// Receita dos dois períodos e de onde veio a variação, uma linha por grupo
function TabelaDecomposicao({ colunaRotulo, linhas }: TabelaDecomposicaoProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{colunaRotulo}</TableHead>
          <TableHead className="text-right">Receita base</TableHead>
          <TableHead className="text-right">Receita comparada</TableHead>
          <TableHead className="text-right">Δ receita</TableHead>
          <TableHead className="text-right">Δ consumo</TableHead>
          <TableHead className="text-right">Efeito volume</TableHead>
          <TableHead className="text-right">Efeito preço</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {linhas.map(({ chave, rotulo, dados }) => (
          <TableRow key={chave}>
            <TableCell className="font-medium">{rotulo}</TableCell>
            <TableCell className={numero}>{formatarMoedaCompacta(dados.receita_p0)}</TableCell>
            <TableCell className={numero}>{formatarMoedaCompacta(dados.receita_p1)}</TableCell>
            <TableCell className="text-right">{variacaoOuTraco(dados.receita_p1, dados.receita_p0)}</TableCell>
            <TableCell className="text-right">{variacaoOuTraco(dados.kwh_p1, dados.kwh_p0)}</TableCell>
            <TableCell className={numero}>{formatarMoedaCompactaComSinal(dados.efeito_volume)}</TableCell>
            <TableCell className={numero}>{formatarMoedaCompactaComSinal(dados.efeito_preco)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

export default TabelaDecomposicao
