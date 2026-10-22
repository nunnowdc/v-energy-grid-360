import { Outlet } from 'react-router'
import AppHeader from '@/components/AppHeader/AppHeader'
import AppSidebar from '@/components/AppSidebar/AppSidebar'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'

function Layout() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <AppHeader />
        <div className="flex flex-1 flex-col gap-4 p-6">
          <Outlet />
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}

export default Layout
