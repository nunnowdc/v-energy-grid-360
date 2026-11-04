import { BadgeCheck, BookOpen, CircleHelp, CircleSlash, ShieldCheck, TriangleAlert } from 'lucide-react'
import type { SeloConfianca as Selo } from '@/hooks/use-agente-ia'
import { cn } from '@/lib/utils'

type Aparencia = { texto: string; explicacao: string; Icone: typeof ShieldCheck; classe: string }

const aparencia: Record<Selo, Aparencia> = {
  certificada: {
    texto: 'Consulta certificada',
    explicacao: 'Veio de uma consulta pronta, validada pelo time de dados',
    Icone: ShieldCheck,
    classe: 'border-primary/30 bg-primary/5 text-primary',
  },
  gerada_confiavel: {
    texto: 'Consulta gerada e validada',
    explicacao: 'A IA escreveu a consulta e ela passou na validação antes de rodar',
    Icone: BadgeCheck,
    classe: 'border-primary/30 bg-primary/5 text-primary',
  },
  documental_rag: {
    texto: 'Baseada em documentos',
    explicacao: 'Veio do glossário e das regras de negócio, não de uma consulta aos dados',
    Icone: BookOpen,
    classe: 'bg-muted/60 text-foreground',
  },
  recusa_honesta: {
    texto: 'Sem resposta segura',
    explicacao: 'A IA preferiu não responder a arriscar um número errado',
    Icone: CircleSlash,
    classe: 'bg-muted/60 text-muted-foreground',
  },
  erro_bloqueado: {
    texto: 'Erro ao responder',
    explicacao: 'O agente falhou no meio do caminho',
    Icone: TriangleAlert,
    classe: 'border-destructive/30 text-destructive',
  },
}

const ehSeloConhecido = (selo: string): selo is Selo => Object.hasOwn(aparencia, selo)

// Quanto dá para confiar na resposta, sempre com ícone e texto (decisão de design)
function SeloConfianca({ selo }: { selo: string }) {
  const { texto, explicacao, Icone, classe } = ehSeloConhecido(selo)
    ? aparencia[selo]
    : { texto: selo, explicacao: 'Selo sem descrição no portal', Icone: CircleHelp, classe: 'bg-muted/60' }

  return (
    <span
      title={explicacao}
      className={cn('inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-xs font-medium', classe)}
    >
      <Icone aria-hidden="true" className="size-3.5" />
      {texto}
    </span>
  )
}

export default SeloConfianca
