import { Navigate } from 'react-router'
import { itensPermitidos } from '@/config/navegacao'
import { useUsuario } from '@/hooks/use-usuario'
import IndicadoresPage from '@/pages/Indicadores/IndicadoresPage'
import SemPermissaoPage from '@/pages/SemPermissao/SemPermissaoPage'

// "/" mostra os Indicadores para quem pode vê-los; os demais perfis
// são levados para a primeira tela que podem abrir
function RotaInicial() {
  const { usuario } = useUsuario()
  const [primeiraTela] = itensPermitidos(usuario.permissoes)

  if (!primeiraTela) {
    return <SemPermissaoPage />
  }

  if (primeiraTela.to === '/') {
    return <IndicadoresPage />
  }

  return <Navigate to={primeiraTela.to} replace />
}

export default RotaInicial
