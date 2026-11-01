import { BadgeCheck, CircleAlert, Sparkles } from 'lucide-react'
import EstadoConsulta from '@/components/EstadoConsulta/EstadoConsulta'
import { Skeleton } from '@/components/ui/skeleton'
import { useInsightIa, type InsightIa as Insight, type TelaInsight } from '@/hooks/use-insight-ia'
import { ErroApi } from '@/lib/api/erro-api'
import { cn } from '@/lib/utils'

const aparenciaSelo = {
  auditado_llm: {
    texto: 'Números conferidos',
    explicacao: 'Cada número do texto foi conferido com os dados consultados',
    Icone: BadgeCheck,
    classe: 'border-primary/30 bg-primary/5 text-primary',
  },
  template_fallback: {
    texto: 'Sem conferência',
    explicacao: 'A IA não conseguiu um texto com os números conferidos',
    Icone: CircleAlert,
    classe: 'bg-muted/60 text-muted-foreground',
  },
}

const ehSeloConhecido = (selo: string): selo is keyof typeof aparenciaSelo => Object.hasOwn(aparenciaSelo, selo)

// Se dá para confiar nos números do texto, com ícone e texto (decisão de design)
function SeloInsight({ selo }: { selo: string }) {
  if (!ehSeloConhecido(selo)) {
    return null
  }
  const { texto, explicacao, Icone, classe } = aparenciaSelo[selo]
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

// Na primeira vez a IA escreve o texto na hora, o que pode levar alguns segundos
function Gerando() {
  return (
    <div className="flex flex-col gap-2">
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-11/12" />
      <Skeleton className="h-4 w-2/3" />
      <p className="text-xs text-muted-foreground">A IA está analisando os dados…</p>
    </div>
  )
}

function Texto({ insight }: { insight: Insight }) {
  const conferido = insight.selo === 'auditado_llm'
  return (
    <div className="flex flex-col gap-1.5">
      <p className={conferido ? 'text-[15px] leading-relaxed' : 'text-sm text-muted-foreground'}>
        {insight.insight_texto}
      </p>
      {insight.fontes && insight.fontes.length > 0 && (
        <p className="text-xs text-muted-foreground">Fonte: {insight.fontes.join(', ')}</p>
      )}
    </div>
  )
}

type InsightIaProps = {
  tela: TelaInsight
  entidadeId: string
  // Do que o insight fala, ex.: "Sobre esta unidade consumidora"
  descricao: string
  className?: string
}

// Caixa com o texto que a IA escreveu sobre os dados da tela, como no wireframe:
// borda tracejada na cor principal e o brilho do agente, para se destacar dos
// blocos de dados e não se confundir com o bloco de destaque (lâmpada, borda contínua)
function InsightIa({ tela, entidadeId, descricao, className }: InsightIaProps) {
  const consulta = useInsightIa(tela, entidadeId)

  // Perfil sem acesso a este insight: a tela segue sem a caixa
  if (consulta.error instanceof ErroApi && consulta.error.status === 403) {
    return null
  }

  return (
    <section
      aria-label="Insight da IA"
      className={cn(
        'flex flex-col gap-2 rounded-xl border-2 border-dashed border-primary/50 bg-primary/5 px-4 py-3',
        className,
      )}
    >
      <div className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm">
        <Sparkles aria-hidden="true" className="size-4 shrink-0 text-marca-energia" />
        <h2 className="font-semibold">Insight da IA</h2>
        <span className="text-muted-foreground">· {descricao}</span>
        {consulta.data && (
          <span className="ml-auto">
            <SeloInsight selo={consulta.data.selo} />
          </span>
        )}
      </div>
      <EstadoConsulta consulta={consulta} esqueleto={<Gerando />}>
        {(insight) => <Texto insight={insight} />}
      </EstadoConsulta>
      <p className="text-xs text-muted-foreground">
        Gerado por IA a partir da base Gold. Confira os números na tela antes de usá-los numa decisão.
      </p>
    </section>
  )
}

export default InsightIa
