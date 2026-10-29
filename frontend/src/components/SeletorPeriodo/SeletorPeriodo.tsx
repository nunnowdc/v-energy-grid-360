import { ChevronDownIcon, ChevronLeft, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverDescription, PopoverTitle, PopoverTrigger } from '@/components/ui/popover'
import { formatarCompetencia, formatarPeriodo } from '@/lib/formatacao'
import { periodoDeTamanho, type AtalhoPeriodo, type Periodo } from '@/lib/periodos'
import { cn } from '@/lib/utils'

const nomesMeses = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']

type SeletorPeriodoProps = {
  rotulo: string
  // Meses da base (yyyy-MM), em ordem
  competencias: string[]
  // Período em vigor (o escolhido ou o padrão da tela)
  valor: Periodo
  // Se o período inteiro pode ser escolhido (ex.: cabe a comparação na base)
  valido: (periodo: Periodo) => boolean
  // Com tamanho fixo, um clique escolhe o começo e o fim vem junto (o comparado da Receita)
  tamanhoFixo?: number
  atalhos: AtalhoPeriodo[]
  tituloAtalhos?: string
  className?: string
  aoMudar: (periodo: Periodo) => void
}

// Filtro de período: o botão mostra o intervalo, como os outros filtros, e abre um
// calendário de meses. Clica no primeiro e no último mês (ou só no primeiro, com
// tamanho fixo). Meses apagados não deixam espaço para a comparação
function SeletorPeriodo({
  rotulo,
  competencias,
  valor,
  valido,
  tamanhoFixo,
  atalhos,
  tituloAtalhos = 'Atalhos',
  className,
  aoMudar,
}: SeletorPeriodoProps) {
  const [aberto, setAberto] = useState(false)
  const [ano, setAno] = useState(() => Number(valor.de.slice(0, 4)))
  // Primeiro mês já clicado, esperando o último
  const [inicio, setInicio] = useState<string>()

  const anos = [...new Set(competencias.map((mes) => Number(mes.slice(0, 4))))]
  const rotuloAtual = formatarPeriodo(valor.de, valor.ate)
  // Nome lido pelo leitor de tela e mostrado ao passar o mouse, ex.: "Período: jul/2025 – jun/2026"
  const descricao = `${rotulo}: ${rotuloAtual}`
  // Destaque no calendário: o começo já clicado ou o período em vigor
  const destaque = inicio ? { de: inicio, ate: inicio } : valor

  function abrirOuFechar(abrir: boolean) {
    setAberto(abrir)
    if (abrir) {
      setAno(Number(valor.de.slice(0, 4)))
      setInicio(undefined)
    }
  }

  function escolher(periodo: Periodo) {
    aoMudar(periodo)
    setAberto(false)
  }

  function periodoDoClique(mes: string): Periodo | undefined {
    if (tamanhoFixo) {
      return periodoDeTamanho(competencias, mes, tamanhoFixo)
    }
    return inicio && mes >= inicio ? { de: inicio, ate: mes } : undefined
  }

  function podeClicar(mes: string) {
    if (!competencias.includes(mes)) {
      return false
    }
    const periodo = periodoDoClique(mes)
    // Sem período fechado, o clique marca o começo: vale se ao menos um mês a partir dele vale
    return periodo ? valido(periodo) : valido({ de: mes, ate: mes })
  }

  function clicar(mes: string) {
    const periodo = periodoDoClique(mes)
    if (periodo) {
      escolher(periodo)
    } else {
      setInicio(mes)
    }
  }

  let instrucao = 'Clique no primeiro e depois no último mês.'
  if (tamanhoFixo) {
    instrucao = `Clique no primeiro mês: o período tem ${tamanhoFixo} ${tamanhoFixo === 1 ? 'mês' : 'meses'}, como o base.`
  } else if (inicio) {
    instrucao = `Começa em ${formatarCompetencia(inicio)}. Agora clique no último mês.`
  }

  return (
    <Popover open={aberto} onOpenChange={abrirOuFechar}>
      <PopoverTrigger
        aria-label={descricao}
        title={descricao}
        className={cn(
          'flex h-9 w-full cursor-pointer items-center gap-1.5 rounded-md border border-input bg-card pr-2.5 pl-3 text-[13px] whitespace-nowrap transition-colors outline-none select-none hover:border-foreground/25 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 data-popup-open:border-ring dark:bg-input/30',
          className,
        )}
      >
        <span className="shrink-0 text-muted-foreground">{rotulo}</span>
        <span className="min-w-0 flex-1 truncate text-left font-semibold text-foreground">{rotuloAtual}</span>
        <ChevronDownIcon aria-hidden="true" className="pointer-events-none size-4 shrink-0 text-muted-foreground" />
      </PopoverTrigger>
      <PopoverContent align="start" className="w-80 gap-3 p-3">
        <div className="flex flex-col gap-0.5">
          <PopoverTitle>{rotulo}</PopoverTitle>
          <PopoverDescription className="text-xs">{instrucao}</PopoverDescription>
        </div>

        <div className="flex items-center justify-between">
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Ano anterior"
            disabled={ano <= anos[0]}
            onClick={() => setAno(ano - 1)}
          >
            <ChevronLeft />
          </Button>
          <span className="text-sm font-semibold tabular-nums">{ano}</span>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Próximo ano"
            disabled={ano >= (anos.at(-1) ?? ano)}
            onClick={() => setAno(ano + 1)}
          >
            <ChevronRight />
          </Button>
        </div>

        <div className="grid grid-cols-4 gap-1">
          {nomesMeses.map((nome, posicao) => {
            const mes = `${ano}-${String(posicao + 1).padStart(2, '0')}`
            const ponta = mes === destaque.de || mes === destaque.ate
            const dentro = mes > destaque.de && mes < destaque.ate
            return (
              <button
                key={mes}
                type="button"
                aria-label={formatarCompetencia(mes)}
                aria-pressed={ponta || dentro}
                disabled={!podeClicar(mes)}
                className={cn(
                  'h-8 cursor-pointer rounded-md text-[13px] transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:text-muted-foreground/40 disabled:hover:bg-transparent',
                  dentro && 'bg-primary/10 text-primary',
                  ponta && 'bg-primary font-semibold text-primary-foreground hover:bg-primary/90',
                )}
                onClick={() => clicar(mes)}
              >
                {nome}
              </button>
            )
          })}
        </div>

        {atalhos.length > 0 && (
          <div className="flex flex-col gap-1.5 border-t pt-2.5">
            <span className="text-xs text-muted-foreground">{tituloAtalhos}</span>
            <div className="flex flex-wrap gap-1">
              {atalhos.map(({ rotulo: nomeAtalho, periodo }) => (
                <Button
                  key={nomeAtalho}
                  size="sm"
                  variant={periodo.de === valor.de && periodo.ate === valor.ate ? 'secondary' : 'outline'}
                  onClick={() => escolher(periodo)}
                >
                  {nomeAtalho}
                </Button>
              ))}
            </div>
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}

export default SeletorPeriodo
