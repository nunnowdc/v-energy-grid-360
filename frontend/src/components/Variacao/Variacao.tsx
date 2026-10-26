import { formatarPercentualComSinal } from '@/lib/formatacao'

type VariacaoProps = {
  // Percentual em pontos (8 = 8%)
  percentual: number
  // Texto depois do número, ex.: "vs. período anterior"
  complemento?: string
}

function escolherSeta(percentualArredondado: number) {
  if (percentualArredondado > 0) {
    return '▲'
  }
  if (percentualArredondado < 0) {
    return '▼'
  }
  return '▬'
}

// Variação sem cor: seta, sinal e número em cinza-escuro (decisão de design)
function Variacao({ percentual, complemento }: VariacaoProps) {
  // Arredonda como o texto (1 casa) para a seta nunca contradizer o número
  const seta = escolherSeta(Math.round(percentual * 10) / 10)

  return (
    <span className="font-mono text-[13px] text-foreground/75">
      <span aria-hidden="true">{seta} </span>
      {formatarPercentualComSinal(percentual)}
      {complemento && <span className="font-sans text-muted-foreground"> {complemento}</span>}
    </span>
  )
}

export default Variacao
