import { NavLink, useLocation } from 'react-router'
import MarcaVEnergy from '@/components/MarcaVEnergy/MarcaVEnergy'
import RodapeUsuario from '@/components/RodapeUsuario/RodapeUsuario'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from '@/components/ui/sidebar'
import { estaAtivo, gruposNavegacao, itensPermitidos } from '@/config/navegacao'
import { useUsuario } from '@/hooks/use-usuario'

function AppSidebar() {
  const { pathname } = useLocation()
  const { usuario } = useUsuario()
  const permitidos = itensPermitidos(usuario.permissoes)

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="pt-4">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              size="lg"
              tooltip="V-Energy Grid 360"
              className="hover:bg-transparent active:bg-transparent"
              render={<NavLink to="/" />}
            >
              <MarcaVEnergy />
              <div className="grid flex-1 text-left leading-tight">
                <span className="truncate text-[15px] font-bold text-sidebar-accent-foreground">
                  V-Energy
                </span>
                <span className="truncate tabular-nums text-[11px] tracking-[0.15em] text-sidebar-muted">
                  GRID 360
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent className="pt-2">
        {gruposNavegacao.map((grupo) => {
          const itens = permitidos.filter((item) => item.grupo === grupo)
          // Grupo sem nenhuma tela permitida não aparece
          if (itens.length === 0) {
            return null
          }

          return (
            <SidebarGroup key={grupo}>
              <SidebarGroupLabel className="tabular-nums text-[11px] tracking-[0.1em] text-sidebar-muted uppercase">
                {grupo}
              </SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {itens.map((item) => (
                    <SidebarMenuItem key={item.to}>
                      <SidebarMenuButton
                        tooltip={item.label}
                        isActive={estaAtivo(pathname, item.to)}
                        className="h-10"
                        render={<NavLink to={item.to} />}
                      >
                        <item.icone />
                        <span>{item.label}</span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          )
        })}
      </SidebarContent>

      <SidebarFooter className="pb-4">
        <RodapeUsuario />
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  )
}

export default AppSidebar
