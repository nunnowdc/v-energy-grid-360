import { corDoTom, tomDaVariacao, type Sentido } from '@/lib/comparacao'
import { formatarPercentualComSinal } from '@/lib/formatacao'
import { cn } from '@/lib/utils'

type VariacaoProps = {
  // Percentual em pontos (8 = 8%)
  percentual: number
  // Para que lado a medida melhora. Sem sentido, a variação fica em cinza-escuro
  sentido?: Sentido
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

// Leitor de tela não vê a cor: ouve se a variação é boa ou ruim
const textoDoTom = { positivo: ' (melhora)', negativo: ' (piora)', neutro: '' }

// Seta, sinal e número: verde quando melhora e vermelho quando piora (decisão de design)
function Variacao({ percentual, sentido, complemento }: VariacaoProps) {
  // Arredonda como o texto (1 casa) para a seta e a cor nunca contradizerem o número
  const arredondado = Math.round(percentual * 10) / 10
  const tom = tomDaVariacao(arredondado, sentido)

  return (
    <span className="tabular-nums text-[13px]">
      <span className={cn(corDoTom[tom], tom !== 'neutro' && 'font-medium')}>
        <span aria-hidden="true">{escolherSeta(arredondado)} </span>
        {formatarPercentualComSinal(percentual)}
        <span className="sr-only">{textoDoTom[tom]}</span>
      </span>
      {complemento && <span className="text-muted-foreground"> {complemento}</span>}
    </span>
  )
}

export default Variacao
