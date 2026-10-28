import { Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'

type BotaoAgenteProps = {
  aberto: boolean
  aoAlternar: () => void
}

// Abre e fecha o agente de IA ao lado da tela; no celular fica só o ícone
function BotaoAgente({ aberto, aoAlternar }: BotaoAgenteProps) {
  return (
    <Button
      variant={aberto ? 'secondary' : 'outline'}
      size="sm"
      aria-label="Agente de IA"
      aria-expanded={aberto}
      aria-controls="painel-agente"
      onClick={aoAlternar}
    >
      <Sparkles className="text-primary" />
      <span className="hidden sm:inline">Agente de IA</span>
    </Button>
  )
}

export default BotaoAgente
