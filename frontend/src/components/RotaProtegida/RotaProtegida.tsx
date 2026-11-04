import { Outlet } from 'react-router'
import type { Permissao } from '@/config/perfis'
import { useUsuario } from '@/hooks/use-usuario'
import SemPermissaoPage from '@/pages/SemPermissao/SemPermissaoPage'

type RotaProtegidaProps = {
  permissao: Permissao
}

// Quem não tem a permissão já não vê o link no menu. Esta proteção cobre
// quem digita o endereço ou abre um link compartilhado
function RotaProtegida({ permissao }: RotaProtegidaProps) {
  const { pode } = useUsuario()

  return pode(permissao) ? <Outlet /> : <SemPermissaoPage />
}

export default RotaProtegida
