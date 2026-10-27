import { Outlet } from 'react-router'
import AppHeader from '@/components/AppHeader/AppHeader'
import AppSidebar from '@/components/AppSidebar/AppSidebar'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'

function Layout() {
  return (
    <SidebarProvider>
      <AppSidebar />
      {/* min-w-0: tabela larga rola dentro do próprio cartão, sem alargar a página */}
      <SidebarInset className="min-w-0 bg-canvas">
        <AppHeader />
        <div className="mx-auto flex w-full max-w-[1240px] min-w-0 flex-1 flex-col gap-6 px-4 py-6 sm:px-8 sm:py-7">
          <Outlet />
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}

export default Layout
