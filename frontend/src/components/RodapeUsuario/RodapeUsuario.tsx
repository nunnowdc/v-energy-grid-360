import { LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { nomesPerfis } from '@/config/perfis'
import { useSair, useUsuario } from '@/hooks/use-usuario'

// "Maria Souza" → "MS"
function iniciais(nome: string) {
  return nome
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((parte) => parte[0].toUpperCase())
    .join('')
}

// Usuário logado no rodapé do menu, com o botão de sair.
// Com o menu recolhido, só o avatar aparece
function RodapeUsuario() {
  const { usuario } = useUsuario()
  const sair = useSair()

  return (
    <div className="flex items-center gap-2.5 border-t border-sidebar-border px-2 pt-3 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0">
      <span
        aria-hidden="true"
        className="flex size-8 shrink-0 items-center justify-center rounded-full bg-sidebar-primary text-xs font-semibold text-sidebar-primary-foreground"
      >
        {iniciais(usuario.nome)}
      </span>
      <div className="grid min-w-0 flex-1 leading-tight group-data-[collapsible=icon]:hidden">
        <span className="truncate text-[13px] font-semibold text-sidebar-accent-foreground">
          {usuario.nome}
        </span>
        <span className="truncate text-xs text-sidebar-muted">{nomesPerfis[usuario.perfil]}</span>
      </div>
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="Sair"
        title="Sair"
        disabled={sair.isPending}
        className="text-sidebar-muted hover:bg-sidebar-accent hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:hidden"
        onClick={() => sair.mutate()}
      >
        <LogOut />
      </Button>
    </div>
  )
}

export default RodapeUsuario
