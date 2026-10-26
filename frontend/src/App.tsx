import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { BrowserRouter, Route, Routes } from 'react-router'
import Layout from './components/Layout/Layout'
import RotaInicial from './components/RotaInicial/RotaInicial'
import RotaProtegida from './components/RotaProtegida/RotaProtegida'
import { TooltipProvider } from './components/ui/tooltip'
import { queryClient } from './lib/api/query-client'
import ContinuidadePage from './pages/Continuidade/ContinuidadePage'
import InspecoesPage from './pages/Inspecoes/InspecoesPage'
import LoginPage from './pages/Login/LoginPage'
import NotFoundPage from './pages/NotFound/NotFoundPage'
import ReceitaPage from './pages/Receita/ReceitaPage'
import Visao360Page from './pages/Visao360/Visao360Page'

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
          <Routes>
            {/* O login fica fora do Layout: sem menu nem cabeçalho */}
            <Route path="login" element={<LoginPage />} />
            <Route element={<Layout />}>
              <Route index element={<RotaInicial />} />
              <Route element={<RotaProtegida permissao="ver_receita" />}>
                <Route path="receita" element={<ReceitaPage />} />
              </Route>
              <Route element={<RotaProtegida permissao="ver_visao_360" />}>
                <Route path="visao-360" element={<Visao360Page />} />
                <Route path="visao-360/:idUc" element={<Visao360Page />} />
              </Route>
              <Route element={<RotaProtegida permissao="ver_fila_inspecao" />}>
                <Route path="inspecoes" element={<InspecoesPage />} />
              </Route>
              <Route element={<RotaProtegida permissao="ver_continuidade" />}>
                <Route path="continuidade" element={<ContinuidadePage />} />
              </Route>
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
      <ReactQueryDevtools />
    </QueryClientProvider>
  )
}

export default App
