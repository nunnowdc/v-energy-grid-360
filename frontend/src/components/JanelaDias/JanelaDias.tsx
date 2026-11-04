import { Button } from '@/components/ui/button'
import { janelasDias, type JanelaDias as Janela } from '@/hooks/use-uso-agente'

type JanelaDiasProps = {
  valor: Janela
  aoMudar: (dias: Janela) => void
}

// Últimos 7, 30 ou 90 dias, terminando hoje: um clique troca a janela
function JanelaDias({ valor, aoMudar }: JanelaDiasProps) {
  return (
    <div role="group" aria-label="Período" className="inline-flex h-9 items-center gap-0.5 self-start rounded-md border bg-card p-0.5">
      {janelasDias.map((dias) => (
        <Button
          key={dias}
          type="button"
          size="sm"
          variant={dias === valor ? 'secondary' : 'ghost'}
          aria-pressed={dias === valor}
          className="h-7 px-3 text-[13px]"
          onClick={() => aoMudar(dias)}
        >
          Últimos {dias} dias
        </Button>
      ))}
    </div>
  )
}

export default JanelaDias
