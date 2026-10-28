import type { ReactNode } from 'react'
import { useLocation } from 'react-router'
import SeloBase from '@/components/SeloBase/SeloBase'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { buscarItemAtual } from '@/config/navegacao'
import { useUsuario } from '@/hooks/use-usuario'

type AppHeaderProps = {
  // Botões no canto direito, ex.: o que abre o agente de IA
  acoes?: ReactNode
}

function AppHeader({ acoes }: AppHeaderProps) {
  const { pathname } = useLocation()
  const { pode } = useUsuario()
  const item = buscarItemAtual(pathname)

  // Trilha "Grupo / Tela"; o título grande fica no cabeçalho da própria página
  let trilha = ['Página não encontrada']
  if (item) {
    trilha = pode(item.permissao) ? [item.grupo, item.label] : ['Sem permissão']
  }

  return (
    <header className="sticky top-0 z-10 flex h-14 shrink-0 items-center gap-2 border-b bg-card px-4">
      <SidebarTrigger className="-ml-1" />
      {/* Ocupa a altura toda do cabeçalho; a margem deixa só o trecho do meio */}
      <Separator orientation="vertical" className="my-5 mr-2" />
      <nav aria-label="Você está em" className="text-sm text-muted-foreground">
        <ol className="flex items-center gap-1.5">
          {trilha.map((parte, indice) => {
            const atual = indice === trilha.length - 1
            return (
              <li key={parte} className="flex items-center gap-1.5">
                {indice > 0 && <span aria-hidden="true">/</span>}
                <span
                  aria-current={atual ? 'page' : undefined}
                  className={atual ? 'font-semibold text-foreground' : undefined}
                >
                  {parte}
                </span>
              </li>
            )
          })}
        </ol>
      </nav>

      <div className="ml-auto flex items-center gap-3">
        <div className="hidden sm:block">
          <SeloBase />
        </div>
        {acoes}
      </div>
    </header>
  )
}

export default AppHeader
