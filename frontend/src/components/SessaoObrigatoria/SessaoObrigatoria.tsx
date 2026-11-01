import { Navigate, Outlet, useLocation } from 'react-router'
import CarregandoPortal from '@/components/CarregandoPortal/CarregandoPortal'
import EstadoErro from '@/components/EstadoErro/EstadoErro'
import { useSessao } from '@/hooks/use-usuario'
import { enderecoDoLogin } from '@/lib/api/sessao'

// Porta da área logada: espera o GET /api/auth/me e só então mostra as telas.
// Sem ninguém logado, vai para o login e guarda a tela pedida para voltar a ela
function SessaoObrigatoria() {
  const sessao = useSessao()
  const { pathname, search } = useLocation()

  if (sessao.isPending) {
    return <CarregandoPortal />
  }

  if (sessao.isError) {
    return (
      <main className="flex min-h-svh items-center justify-center bg-canvas p-4">
        <EstadoErro mensagem={sessao.error.message} aoTentarDeNovo={() => sessao.refetch()} />
      </main>
    )
  }

  if (!sessao.data) {
    return <Navigate to={enderecoDoLogin({ voltar: pathname + search })} replace />
  }

  return <Outlet />
}

export default SessaoObrigatoria
