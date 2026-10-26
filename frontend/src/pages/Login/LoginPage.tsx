import { Link, useSearchParams } from 'react-router'
import MarcaVEnergy from '@/components/MarcaVEnergy/MarcaVEnergy'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { MOTIVO_SESSAO_EXPIRADA } from '@/lib/api/sessao'

// Por enquanto só avisa que a sessão expirou. O formulário de e-mail e senha
// entra quando o backend tiver o POST /api/auth/login
function LoginPage() {
  const [params] = useSearchParams()
  const sessaoExpirada = params.get('motivo') === MOTIVO_SESSAO_EXPIRADA

  return (
    <main className="flex min-h-svh items-center justify-center bg-canvas p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="justify-items-center text-center">
          <MarcaVEnergy className="size-10 p-[9px]" />
          <CardTitle className="text-lg font-bold">Entrar no portal</CardTitle>
          <CardDescription>V-Energy Grid 360</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {sessaoExpirada && (
            <p role="alert" className="rounded-lg border bg-muted px-3 py-2 text-sm">
              Sua sessão expirou. Entre novamente.
            </p>
          )}
          <p className="text-sm text-muted-foreground">
            O login ainda não está ligado ao backend. Enquanto isso, o portal usa o usuário
            de teste definido no <code>.env.local</code>.
          </p>
          <Button nativeButton={false} render={<Link to="/" />}>
            Continuar com o usuário de teste
          </Button>
        </CardContent>
      </Card>
    </main>
  )
}

export default LoginPage
