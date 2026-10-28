import { useState } from 'react'
import { Outlet } from 'react-router'
import AppHeader from '@/components/AppHeader/AppHeader'
import AppSidebar from '@/components/AppSidebar/AppSidebar'
import BotaoAgente from '@/components/BotaoAgente/BotaoAgente'
import PainelAgente from '@/components/PainelAgente/PainelAgente'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { useUsuario } from '@/hooks/use-usuario'

function Layout() {
  const { pode } = useUsuario()
  const [agenteAberto, setAgenteAberto] = useState(false)
  const usaAgente = pode('usar_agente_ia')

  return (
    <SidebarProvider>
      <AppSidebar />
      {/* min-w-0: tabela larga rola dentro do próprio cartão, sem alargar a página */}
      <SidebarInset className="min-w-0 bg-canvas">
        <AppHeader
          acoes={
            usaAgente && (
              <BotaoAgente aberto={agenteAberto} aoAlternar={() => setAgenteAberto((aberto) => !aberto)} />
            )
          }
        />
        <div className="mx-auto flex w-full max-w-[1240px] min-w-0 flex-1 flex-col gap-6 px-4 py-6 sm:px-8 sm:py-7">
          <Outlet />
        </div>
      </SidebarInset>
      {/* O agente divide a tela com o dashboard, que continua utilizável ao lado */}
      {usaAgente && <PainelAgente aberto={agenteAberto} aoFechar={() => setAgenteAberto(false)} />}
    </SidebarProvider>
  )
}

export default Layout
