import { nomesPerfis } from '@/config/perfis'
import { useUsuario } from '@/hooks/use-usuario'

// "Teste Administrador (TI)" → "TA"
function iniciais(nome: string) {
  return nome
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((parte) => parte[0].toUpperCase())
    .join('')
}

// Usuário logado no rodapé do menu. Com o menu recolhido, só o avatar aparece
function RodapeUsuario() {
  const { usuario } = useUsuario()

  return (
    <div className="flex items-center gap-2.5 border-t border-sidebar-border px-2 pt-3 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0">
      <span
        aria-hidden="true"
        className="flex size-8 shrink-0 items-center justify-center rounded-full bg-sidebar-primary text-xs font-semibold text-sidebar-primary-foreground"
      >
        {iniciais(usuario.nome)}
      </span>
      <div className="grid min-w-0 leading-tight group-data-[collapsible=icon]:hidden">
        <span className="truncate text-[13px] font-semibold text-sidebar-accent-foreground">
          {usuario.nome}
        </span>
        <span className="truncate text-xs text-sidebar-muted">{nomesPerfis[usuario.perfil]}</span>
      </div>
    </div>
  )
}

export default RodapeUsuario
