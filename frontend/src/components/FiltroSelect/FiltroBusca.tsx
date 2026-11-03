import {
  Combobox,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
  ComboboxTrigger,
} from '@/components/ui/combobox'
import { cn } from '@/lib/utils'

type Item = { value: string | null; label: string }

type FiltroBuscaProps = {
  rotulo: string
  itens: Item[]
  selecionado?: Item
  desabilitado?: boolean
  // Visual do botão, o mesmo do filtro sem busca
  className: string
  aoMudar: (valor?: string) => void
}

// Filtro de lista longa (ex.: os bairros do Recife, os alimentadores): o mesmo botão
// "Bairro Todos ▾", mas a lista abre com um campo de busca em cima. A busca ignora
// acentos e maiúsculas ("jaboatao" acha "Jaboatão")
function FiltroBusca({ rotulo, itens, selecionado, desabilitado, className, aoMudar }: FiltroBuscaProps) {
  const descricao = `${rotulo}: ${selecionado?.label}`

  return (
    <Combobox
      items={itens}
      value={selecionado ?? null}
      disabled={desabilitado}
      // O primeiro resultado da busca fica marcado: digitar e apertar Enter já escolhe
      autoHighlight
      isItemEqualToValue={(item, valor) => item.value === valor.value}
      onValueChange={(item) => aoMudar(item?.value ?? undefined)}
    >
      <ComboboxTrigger
        aria-label={descricao}
        title={descricao}
        className={cn(
          'flex items-center justify-between border border-input whitespace-nowrap transition-colors outline-none select-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-50',
          className,
        )}
      >
        <span className="shrink-0 text-muted-foreground">{rotulo}</span>
        <span className="min-w-0 flex-1 truncate text-left font-semibold text-foreground">{selecionado?.label}</span>
      </ComboboxTrigger>
      <ComboboxContent className="min-w-(--anchor-width) rounded-md shadow-lg ring-border">
        <ComboboxInput showTrigger={false} placeholder="Buscar…" aria-label={`Buscar ${rotulo.toLowerCase()}`} />
        <ComboboxEmpty>Nada encontrado.</ComboboxEmpty>
        <ComboboxList className="max-h-72">
          {(item: Item) => (
            <ComboboxItem
              key={item.value ?? ''}
              value={item}
              className="cursor-pointer py-1.5 pl-2 text-[13px] data-selected:font-semibold data-selected:text-primary [&_svg]:text-primary"
            >
              {item.label}
            </ComboboxItem>
          )}
        </ComboboxList>
      </ComboboxContent>
    </Combobox>
  )
}

export default FiltroBusca
