import { Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'

type BotaoAgenteProps = {
  aberto: boolean
  aoAlternar: () => void
}

// Abre e fecha o agente de IA ao lado da tela; no celular fica só o ícone.
// Fechado, é o botão de destaque do cabeçalho (petróleo cheio): é a ação mais
// importante do portal depois dos filtros. Aberto, fica discreto ao lado do painel
function BotaoAgente({ aberto, aoAlternar }: BotaoAgenteProps) {
  return (
    <Button
      variant={aberto ? 'secondary' : 'default'}
      aria-label="Agente de IA"
      aria-expanded={aberto}
      aria-controls="painel-agente"
      className="h-9 px-3 font-semibold shadow-sm"
      onClick={aoAlternar}
    >
      <Sparkles className={aberto ? 'text-primary' : undefined} />
      <span className="hidden sm:inline">Agente de IA</span>
    </Button>
  )
}

export default BotaoAgente
