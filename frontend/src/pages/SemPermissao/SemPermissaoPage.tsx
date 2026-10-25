import { Lock } from 'lucide-react'
import { Link, useLocation } from 'react-router'
import { Button } from '@/components/ui/button'
import { buscarItemAtual } from '@/config/navegacao'
import { nomesPerfis } from '@/config/perfis'
import { useUsuario } from '@/hooks/use-usuario'

function SemPermissaoPage() {
  const { pathname } = useLocation()
  const { usuario } = useUsuario()
  const tela = buscarItemAtual(pathname)?.label ?? 'esta tela'

  return (
    <section className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
      <Lock className="size-10 text-muted-foreground" />
      <h2 className="text-lg font-semibold">Você não tem acesso a esta tela</h2>
      <p className="max-w-md text-sm text-muted-foreground">
        O seu perfil ({nomesPerfis[usuario.perfil]}) não inclui a tela {tela}.
        Se precisar de acesso, fale com a equipe de TI.
      </p>
      <Button className="mt-2" nativeButton={false} render={<Link to="/" />}>
        Voltar ao início
      </Button>
    </section>
  )
}

export default SemPermissaoPage
