import { ChevronRight } from 'lucide-react'
import ValorEfeito from '@/components/ValorEfeito/ValorEfeito'
import Variacao from '@/components/Variacao/Variacao'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { DecomposicaoCompleta } from '@/hooks/use-receita'
import { variacaoPercentual } from '@/lib/comparacao'
import { formatarMoedaCompacta } from '@/lib/formatacao'

type LinhaDecomposicao = {
  chave: string
  rotulo: string
  dados: DecomposicaoCompleta
}

type TabelaDecomposicaoProps = {
  // Título da primeira coluna, ex.: "Município"
  colunaRotulo: string
  linhas: LinhaDecomposicao[]
  // Clicar numa linha recebe a chave dela. Sem ação, as linhas são só leitura
  aoClicar?: (chave: string) => void
  // O que o clique faz, escrito no fim de cada linha (ex.: "Ver bairros")
  textoAcao?: string
}

const numero = 'text-right tabular-nums'

// Receita e consumo maiores são bons para a distribuidora
function variacaoOuTraco(atual: number, anterior: number) {
  const variacao = variacaoPercentual(atual, anterior)
  return variacao === undefined ? (
    <span className="text-muted-foreground">—</span>
  ) : (
    <Variacao percentual={variacao} sentido="subir-e-bom" />
  )
}

// Receita dos dois períodos e de onde veio a variação, uma linha por grupo.
// Com ação, a linha inteira é clicável: o botão do nome se estica por cima dela
// (after:inset-0), então o clique, o teclado e o leitor de tela usam o mesmo botão
function TabelaDecomposicao({ colunaRotulo, linhas, aoClicar, textoAcao }: TabelaDecomposicaoProps) {
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
          {aoClicar && (
            <TableHead>
              <span className="sr-only">Detalhar</span>
            </TableHead>
          )}
        </TableRow>
      </TableHeader>
      <TableBody>
        {linhas.map(({ chave, rotulo, dados }) => (
          <TableRow key={chave} className={aoClicar ? 'group relative cursor-pointer hover:bg-primary/5' : undefined}>
            <TableCell className="font-medium">
              {aoClicar ? (
                <button
                  type="button"
                  onClick={() => aoClicar(chave)}
                  className="cursor-pointer text-left text-primary outline-none group-hover:underline after:absolute after:inset-0 focus-visible:after:ring-2 focus-visible:after:ring-ring focus-visible:after:ring-inset"
                >
                  {rotulo}
                </button>
              ) : (
                rotulo
              )}
            </TableCell>
            <TableCell className={numero}>{formatarMoedaCompacta(dados.receita_p0)}</TableCell>
            <TableCell className={numero}>{formatarMoedaCompacta(dados.receita_p1)}</TableCell>
            <TableCell className="text-right">{variacaoOuTraco(dados.receita_p1, dados.receita_p0)}</TableCell>
            <TableCell className="text-right">{variacaoOuTraco(dados.kwh_p1, dados.kwh_p0)}</TableCell>
            <TableCell className="text-right">
              <ValorEfeito reais={dados.efeito_volume} />
            </TableCell>
            <TableCell className="text-right">
              <ValorEfeito reais={dados.efeito_preco} />
            </TableCell>
            {aoClicar && (
              <TableCell className="text-right">
                <span
                  aria-hidden="true"
                  className="inline-flex items-center gap-0.5 text-xs font-medium whitespace-nowrap text-primary"
                >
                  {textoAcao}
                  <ChevronRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
                </span>
              </TableCell>
            )}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

export default TabelaDecomposicao
