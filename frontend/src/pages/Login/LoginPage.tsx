import { useId, useState, type FormEvent } from 'react'
import { Navigate, useSearchParams } from 'react-router'
import CarregandoPortal from '@/components/CarregandoPortal/CarregandoPortal'
import MarcaVEnergy from '@/components/MarcaVEnergy/MarcaVEnergy'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { buscarItemAtual } from '@/config/navegacao'
import { useEntrar, useSessao, type Usuario } from '@/hooks/use-usuario'
import { ErroApi } from '@/lib/api/erro-api'
import { destinoDoVoltar, MOTIVO_SESSAO_EXPIRADA, PARAM_VOLTAR } from '@/lib/api/sessao'

// Volta para a tela pedida antes do login; se o perfil não puder abri-la,
// vai para a primeira tela dele em vez da página "Sem permissão"
function destinoPara(usuario: Usuario, voltar: string | null) {
  const destino = destinoDoVoltar(voltar)
  const item = buscarItemAtual(destino.split('?')[0])
  return item && !usuario.permissoes.includes(item.permissao) ? '/' : destino
}

// O backend responde 401 genérico, sem dizer se o e-mail existe
function mensagemDoErro(erro: Error) {
  if (erro instanceof ErroApi) {
    return erro.status === 401 ? 'E-mail ou senha incorretos.' : erro.message
  }
  return 'Algo deu errado. Tente de novo em instantes.'
}

function LoginPage() {
  const [params] = useSearchParams()
  const sessao = useSessao()
  const entrar = useEntrar()
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [aviso, setAviso] = useState<string>()
  const idEmail = useId()
  const idSenha = useId()
  const idErro = useId()

  if (sessao.isPending) {
    return <CarregandoPortal />
  }

  // Já logado (ou acabou de entrar): segue para o portal
  if (sessao.data) {
    return <Navigate to={destinoPara(sessao.data, params.get(PARAM_VOLTAR))} replace />
  }

  const sessaoExpirada = params.get('motivo') === MOTIVO_SESSAO_EXPIRADA
  const erro = aviso ?? (entrar.error ? mensagemDoErro(entrar.error) : undefined)

  function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    const emailDigitado = email.trim()
    if (!emailDigitado || !senha) {
      setAviso('Preencha o e-mail e a senha.')
      return
    }
    if (!emailDigitado.includes('@')) {
      setAviso('Digite um e-mail válido.')
      return
    }
    setAviso(undefined)
    entrar.mutate({ email: emailDigitado, senha })
  }

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
            <p role="status" className="rounded-lg border bg-muted px-3 py-2 text-sm">
              Sua sessão expirou. Entre novamente.
            </p>
          )}
          {/* noValidate: as mensagens de campo vazio ou inválido são as do portal, em português */}
          <form noValidate className="flex flex-col gap-4" onSubmit={enviar}>
            <div className="flex flex-col gap-1.5">
              <label htmlFor={idEmail} className="text-sm font-medium">
                E-mail
              </label>
              <Input
                id={idEmail}
                type="email"
                autoComplete="username"
                // Mesmo limite do backend (usuarios.email é VARCHAR(255))
                maxLength={255}
                value={email}
                aria-invalid={erro ? true : undefined}
                aria-describedby={erro ? idErro : undefined}
                onChange={(evento) => setEmail(evento.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor={idSenha} className="text-sm font-medium">
                Senha
              </label>
              <Input
                id={idSenha}
                type="password"
                autoComplete="current-password"
                value={senha}
                aria-invalid={erro ? true : undefined}
                aria-describedby={erro ? idErro : undefined}
                onChange={(evento) => setSenha(evento.target.value)}
              />
            </div>
            {erro && (
              <p id={idErro} role="alert" className="text-sm text-destructive">
                {erro}
              </p>
            )}
            <Button type="submit" disabled={entrar.isPending}>
              {entrar.isPending ? 'Entrando…' : 'Entrar'}
            </Button>
          </form>
          <p className="text-center text-xs text-muted-foreground">
            Sem acesso? As contas são criadas pela equipe de TI.
          </p>
        </CardContent>
      </Card>
    </main>
  )
}

export default LoginPage
