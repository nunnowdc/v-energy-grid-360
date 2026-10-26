import { Select, SelectContent, SelectItem, SelectTrigger } from '@/components/ui/select'
import { cn } from '@/lib/utils'

export type OpcaoFiltro = {
  valor: string
  rotulo: string
}

type FiltroSelectProps = {
  rotulo: string
  valor?: string
  opcoes: OpcaoFiltro[]
  // Texto da opção vazia, que significa "sem filtro" (ex.: "Todos")
  textoVazio: string
  desabilitado?: boolean
  // Largura fixa do filtro, para a barra não mudar de lugar quando o valor muda
  className?: string
  aoMudar: (valor?: string) => void
}

// Um filtro compacto: rótulo e valor escolhido no mesmo botão, ex.: "Município Todos ▾".
// O botão inteiro abre a lista; valor longo é cortado com "…" e aparece inteiro ao passar o mouse
function FiltroSelect({ rotulo, valor, opcoes, textoVazio, desabilitado, className, aoMudar }: FiltroSelectProps) {
  // A opção vazia usa null, que é como o Select representa "nada escolhido"
  const itens = [{ value: null, label: textoVazio }, ...opcoes.map(({ valor, rotulo }) => ({ value: valor, label: rotulo }))]
  const rotuloAtual = itens.find((item) => item.value === (valor ?? null))?.label
  // Nome lido pelo leitor de tela e mostrado ao passar o mouse, ex.: "Município: Recife"
  const descricao = `${rotulo}: ${rotuloAtual}`

  return (
    <Select
      items={itens}
      value={valor ?? null}
      disabled={desabilitado}
      onValueChange={(novoValor) => aoMudar(novoValor ?? undefined)}
    >
      <SelectTrigger
        aria-label={descricao}
        title={descricao}
        className={cn(
          'h-9 w-full cursor-pointer gap-1.5 rounded-md bg-card pr-2.5 pl-3 text-[13px] hover:border-foreground/25 disabled:cursor-not-allowed data-popup-open:border-ring',
          className,
        )}
      >
        <span className="shrink-0 text-muted-foreground">{rotulo}</span>
        <span className="min-w-0 flex-1 truncate text-left font-semibold text-foreground">{rotuloAtual}</span>
      </SelectTrigger>
      <SelectContent
        align="start"
        alignItemWithTrigger={false}
        className="max-h-72 min-w-(--anchor-width) rounded-md p-1 shadow-lg ring-border"
      >
        {itens.map((item) => (
          <SelectItem
            key={item.value ?? ''}
            value={item.value}
            className="cursor-pointer py-1.5 pl-2 text-[13px] aria-selected:font-semibold aria-selected:text-primary [&_svg]:text-primary"
          >
            {item.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

export default FiltroSelect
