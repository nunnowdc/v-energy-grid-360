import { BrowserRouter, Route, Routes } from 'react-router'
import Layout from './components/Layout/Layout'
import ContinuidadePage from './pages/Continuidade/ContinuidadePage'
import IndicadoresPage from './pages/Indicadores/IndicadoresPage'
import InspecoesPage from './pages/Inspecoes/InspecoesPage'
import NotFoundPage from './pages/NotFound/NotFoundPage'
import ReceitaPage from './pages/Receita/ReceitaPage'
import Visao360Page from './pages/Visao360/Visao360Page'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<IndicadoresPage />} />
          <Route path="receita" element={<ReceitaPage />} />
          <Route path="visao-360" element={<Visao360Page />} />
          <Route path="visao-360/:idUc" element={<Visao360Page />} />
          <Route path="inspecoes" element={<InspecoesPage />} />
          <Route path="continuidade" element={<ContinuidadePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
