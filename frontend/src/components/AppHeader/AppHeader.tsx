import { CircleUserRound, LogOut } from 'lucide-react'
import { useLocation } from 'react-router'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { buscarItemAtual } from '@/config/navegacao'
import { nomesPerfis } from '@/config/perfis'
import { useUsuario } from '@/hooks/use-usuario'

function AppHeader() {
  const { pathname } = useLocation()
  const { usuario, pode } = useUsuario()
  const item = buscarItemAtual(pathname)

  let titulo = 'Página não encontrada'
  if (item) {
    titulo = pode(item.permissao) ? item.label : 'Sem permissão'
  }

  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="mr-2 h-4" />
      <h1 className="text-base font-semibold">{titulo}</h1>

      {/* Mostra o usuário de teste até o login existir */}
      <div className="ml-auto flex items-center gap-2">
        <CircleUserRound className="size-5 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">
          {usuario.nome} · {nomesPerfis[usuario.perfil]}
        </span>
        <Button variant="ghost" size="sm" disabled>
          <LogOut />
          Sair
        </Button>
      </div>
    </header>
  )
}

export default AppHeader
