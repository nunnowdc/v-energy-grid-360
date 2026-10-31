import { CircleCheck, KeyRound } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import CampoFormulario from '@/components/CampoFormulario/CampoFormulario'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { Input } from '@/components/ui/input'
import { TAMANHO_MINIMO_SENHA, useTrocarSenha } from '@/hooks/use-contas'
import { useUsuario } from '@/hooks/use-usuario'
import { ErroApi } from '@/lib/api/erro-api'

type Campo = 'atual' | 'nova' | 'confirmacao'

function validar(atual: string, nova: string, confirmacao: string) {
  const erros: Partial<Record<Campo, string>> = {}
  if (!atual) {
    erros.atual = 'Preencha a senha atual.'
  }
  if (nova.length < TAMANHO_MINIMO_SENHA) {
    erros.nova = `A nova senha precisa de pelo menos ${TAMANHO_MINIMO_SENHA} caracteres.`
  } else if (nova === atual) {
    erros.nova = 'A nova senha precisa ser diferente da atual.'
  }
  // A confirmação é só do portal: o backend recebe a nova senha uma vez
  if (!erros.nova && confirmacao !== nova) {
    erros.confirmacao = 'As duas senhas novas estão diferentes.'
  }
  return erros
}

// Fica dentro do painel, que só existe aberto: fechar e abrir de novo
// começa com os campos vazios
function Formulario() {
  const { usuario } = useUsuario()
  const trocar = useTrocarSenha()
  const [atual, setAtual] = useState('')
  const [nova, setNova] = useState('')
  const [confirmacao, setConfirmacao] = useState('')
  const [erros, setErros] = useState<Partial<Record<Campo, string>>>({})

  if (trocar.isSuccess) {
    return (
      <>
        <div role="status" className="mx-4 flex gap-2.5 rounded-lg border bg-muted px-3 py-2.5 text-sm">
          <CircleCheck aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-primary" />
          <p>Senha trocada. Você continua conectado; no próximo login, use a senha nova.</p>
        </div>
        <SheetFooter>
          <SheetClose render={<Button />}>Fechar</SheetClose>
        </SheetFooter>
      </>
    )
  }

  function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    const encontrados = validar(atual, nova, confirmacao)
    setErros(encontrados)
    if (Object.keys(encontrados).length > 0) {
      return
    }
    trocar.mutate(
      { senhaAtual: atual, novaSenha: nova },
      {
        onError: (erro) => {
          if (erro instanceof ErroApi && erro.status === 400) {
            setErros({ atual: 'A senha atual está incorreta.' })
          }
        },
      },
    )
  }

  const erroGeral =
    trocar.error && !(trocar.error instanceof ErroApi && trocar.error.status === 400) ? trocar.error.message : undefined

  return (
    // noValidate: as mensagens de campo vazio ou inválido são as do portal, em português
    <form noValidate className="flex flex-1 flex-col" onSubmit={enviar}>
      <div className="flex flex-col gap-4 px-4">
        {/* Para o gerenciador de senhas do navegador saber de qual conta é a senha */}
        <input type="email" name="username" autoComplete="username" value={usuario.email} readOnly hidden />
        <CampoFormulario rotulo="Senha atual" erro={erros.atual}>
          {(atributos) => (
            <Input
              {...atributos}
              type="password"
              autoComplete="current-password"
              value={atual}
              onChange={(evento) => setAtual(evento.target.value)}
            />
          )}
        </CampoFormulario>
        <CampoFormulario rotulo="Nova senha" erro={erros.nova} dica={`Pelo menos ${TAMANHO_MINIMO_SENHA} caracteres.`}>
          {(atributos) => (
            <Input
              {...atributos}
              type="password"
              autoComplete="new-password"
              value={nova}
              onChange={(evento) => setNova(evento.target.value)}
            />
          )}
        </CampoFormulario>
        <CampoFormulario rotulo="Repita a nova senha" erro={erros.confirmacao}>
          {(atributos) => (
            <Input
              {...atributos}
              type="password"
              autoComplete="new-password"
              value={confirmacao}
              onChange={(evento) => setConfirmacao(evento.target.value)}
            />
          )}
        </CampoFormulario>
        {erroGeral && (
          <p role="alert" className="text-sm text-destructive">
            {erroGeral}
          </p>
        )}
      </div>
      <SheetFooter>
        <Button type="submit" disabled={trocar.isPending}>
          {trocar.isPending ? 'Trocando…' : 'Trocar senha'}
        </Button>
      </SheetFooter>
    </form>
  )
}

// Botão do rodapé do menu que abre o painel de troca de senha, para qualquer perfil
function TrocaSenha({ className }: { className?: string }) {
  return (
    <Sheet>
      <SheetTrigger
        render={<Button variant="ghost" size="icon-sm" aria-label="Trocar senha" title="Trocar senha" className={className} />}
      >
        <KeyRound />
      </SheetTrigger>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>Trocar senha</SheetTitle>
          <SheetDescription>Vale para os próximos logins. Você continua conectado.</SheetDescription>
        </SheetHeader>
        <Formulario />
      </SheetContent>
    </Sheet>
  )
}

export default TrocaSenha
