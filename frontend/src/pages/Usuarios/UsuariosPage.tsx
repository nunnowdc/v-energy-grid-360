import { CircleCheck } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import CabecalhoPagina from '@/components/CabecalhoPagina/CabecalhoPagina'
import CampoFormulario from '@/components/CampoFormulario/CampoFormulario'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { itensPermitidos } from '@/config/navegacao'
import { nomesPerfis, permissoesPorPerfil, type Perfil } from '@/config/perfis'
import { TAMANHO_MINIMO_SENHA, useCriarConta } from '@/hooks/use-contas'
import type { UsuarioApi } from '@/hooks/use-usuario'
import { ErroApi } from '@/lib/api/erro-api'

type Campo = 'nome' | 'email' | 'perfil' | 'senha'

type Dados = {
  nome: string
  email: string
  perfil: Perfil | null
  senha: string
}

const DADOS_VAZIOS: Dados = { nome: '', email: '', perfil: null, senha: '' }

const perfis = Object.keys(nomesPerfis) as Perfil[]
const itensPerfil = perfis.map((perfil) => ({ value: perfil, label: nomesPerfis[perfil] }))

const listaEmPortugues = new Intl.ListFormat('pt-BR', { type: 'conjunction' })

// "Indicadores, Receita e Continuidade", a partir do menu de cada perfil
function telasDoPerfil(perfil: Perfil) {
  return listaEmPortugues.format(itensPermitidos(permissoesPorPerfil[perfil]).map((item) => item.label))
}

// Os mesmos limites do backend: assim o formulário avisa antes de enviar
function validar({ nome, email, perfil, senha }: Dados) {
  const erros: Partial<Record<Campo, string>> = {}
  if (!nome.trim()) {
    erros.nome = 'Preencha o nome.'
  }
  if (!email.trim()) {
    erros.email = 'Preencha o e-mail.'
  } else if (!email.includes('@')) {
    erros.email = 'Digite um e-mail válido.'
  }
  if (!perfil) {
    erros.perfil = 'Escolha o perfil.'
  }
  if (senha.length < TAMANHO_MINIMO_SENHA) {
    erros.senha = `A senha precisa de pelo menos ${TAMANHO_MINIMO_SENHA} caracteres.`
  }
  return erros
}

function NovaConta() {
  const criar = useCriarConta()
  const [dados, setDados] = useState(DADOS_VAZIOS)
  const [erros, setErros] = useState<Partial<Record<Campo, string>>>({})
  const [criada, setCriada] = useState<UsuarioApi>()

  function mudar<C extends Campo>(campo: C, valor: Dados[C]) {
    setDados((anteriores) => ({ ...anteriores, [campo]: valor }))
    setErros((anteriores) => ({ ...anteriores, [campo]: undefined }))
  }

  function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    setCriada(undefined)
    const encontrados = validar(dados)
    setErros(encontrados)
    if (Object.keys(encontrados).length > 0 || !dados.perfil) {
      return
    }
    criar.mutate(
      { nome: dados.nome.trim(), email: dados.email.trim(), perfil: dados.perfil, senha: dados.senha },
      {
        onSuccess: (conta) => {
          setCriada(conta)
          setDados(DADOS_VAZIOS)
        },
        onError: (erro) => {
          if (erro instanceof ErroApi && erro.status === 409) {
            setErros({ email: 'Já existe uma conta com este e-mail.' })
          }
        },
      },
    )
  }

  const erroGeral =
    criar.error && !(criar.error instanceof ErroApi && criar.error.status === 409) ? criar.error.message : undefined

  return (
    <Card>
      <CardHeader>
        <CardTitle>Nova conta</CardTitle>
        <CardDescription>
          A pessoa entra no portal com o e-mail e a senha inicial, e vê só as telas do perfil escolhido.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {criada && (
          <div role="status" className="flex gap-2.5 rounded-lg border bg-muted px-3 py-2.5 text-sm">
            <CircleCheck aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-primary" />
            <p>
              Conta criada para <strong>{criada.nome}</strong> ({criada.email}), com o perfil{' '}
              {nomesPerfis[criada.perfil as Perfil] ?? criada.perfil}. Passe a senha inicial para a pessoa e peça
              que ela troque em “Trocar senha”, no rodapé do menu.
            </p>
          </div>
        )}
        {/* noValidate: as mensagens de campo vazio ou inválido são as do portal, em português */}
        <form noValidate className="grid gap-4 sm:grid-cols-2" onSubmit={enviar}>
          <CampoFormulario rotulo="Nome" erro={erros.nome}>
            {(atributos) => (
              <Input
                {...atributos}
                autoComplete="off"
                maxLength={150}
                value={dados.nome}
                onChange={(evento) => mudar('nome', evento.target.value)}
              />
            )}
          </CampoFormulario>
          <CampoFormulario rotulo="E-mail" erro={erros.email}>
            {(atributos) => (
              <Input
                {...atributos}
                type="email"
                autoComplete="off"
                // Mesmo limite do backend (usuarios.email é VARCHAR(255))
                maxLength={255}
                value={dados.email}
                onChange={(evento) => mudar('email', evento.target.value)}
              />
            )}
          </CampoFormulario>
          <CampoFormulario
            rotulo="Perfil"
            erro={erros.perfil}
            dica={dados.perfil ? `Vê ${telasDoPerfil(dados.perfil)}.` : undefined}
          >
            {(atributos) => (
              <Select
                items={itensPerfil}
                value={dados.perfil}
                onValueChange={(perfil) => mudar('perfil', perfil)}
              >
                <SelectTrigger {...atributos} className="h-9 w-full">
                  <SelectValue placeholder="Escolha o perfil" />
                </SelectTrigger>
                <SelectContent alignItemWithTrigger={false}>
                  {itensPerfil.map((item) => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </CampoFormulario>
          <CampoFormulario
            rotulo="Senha inicial"
            erro={erros.senha}
            dica={`Pelo menos ${TAMANHO_MINIMO_SENHA} caracteres.`}
          >
            {(atributos) => (
              <Input
                {...atributos}
                type="password"
                // Senha de outra pessoa: o navegador não deve oferecer a do administrador
                autoComplete="new-password"
                value={dados.senha}
                onChange={(evento) => mudar('senha', evento.target.value)}
              />
            )}
          </CampoFormulario>
          {erroGeral && (
            <p role="alert" className="text-sm text-destructive sm:col-span-2">
              {erroGeral}
            </p>
          )}
          <div className="sm:col-span-2">
            <Button type="submit" disabled={criar.isPending}>
              {criar.isPending ? 'Criando…' : 'Criar conta'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

// O que cada perfil acessa, para escolher o perfil certo
function PerfisETelas() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>O que cada perfil vê</CardTitle>
        <CardDescription>Todos os perfis também usam o agente de IA.</CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="flex flex-col gap-3 text-sm">
          {perfis.map((perfil) => (
            <div key={perfil}>
              <dt className="font-semibold">{nomesPerfis[perfil]}</dt>
              <dd className="text-muted-foreground">{telasDoPerfil(perfil)}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  )
}

function UsuariosPage() {
  return (
    <section className="flex flex-col gap-6">
      <CabecalhoPagina />
      <div className="grid items-start gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <NovaConta />
        </div>
        <PerfisETelas />
      </div>
    </section>
  )
}

export default UsuariosPage
