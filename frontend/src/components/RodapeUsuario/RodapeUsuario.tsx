import { ChevronsUpDown, KeyRound, LogOut, Moon, Sun } from 'lucide-react'
import { useState } from 'react'
import TrocaSenha from '@/components/TrocaSenha/TrocaSenha'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { SidebarMenu, SidebarMenuButton, SidebarMenuItem, useSidebar } from '@/components/ui/sidebar'
import { nomesPerfis } from '@/config/perfis'
import { useTema } from '@/hooks/use-tema'
import { useSair, useUsuario } from '@/hooks/use-usuario'
import type { Tema } from '@/lib/tema'
import { cn } from '@/lib/utils'

// "Maria Souza" → "MS"
function iniciais(nome: string) {
  return nome
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((parte) => parte[0].toUpperCase())
    .join('')
}

function Avatar({ nome, className }: { nome: string; className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn('flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold', className)}
    >
      {iniciais(nome)}
    </span>
  )
}

// Usuário logado no rodapé do menu. Clicar abre o menu da conta, com os dados
// da pessoa, a troca de senha, o tema e o Sair. Com o menu recolhido, só o avatar aparece
function RodapeUsuario() {
  const { usuario } = useUsuario()
  const { isMobile } = useSidebar()
  const sair = useSair()
  const { tema, mudarTema } = useTema()
  const [trocandoSenha, setTrocandoSenha] = useState(false)
  const perfil = nomesPerfis[usuario.perfil]

  return (
    <>
      <SidebarMenu className="border-t border-sidebar-border pt-2">
        <SidebarMenuItem>
          {/* Cada vez que o menu abre, some o erro de uma tentativa anterior de sair */}
          <DropdownMenu onOpenChange={(aberto) => aberto && sair.reset()}>
            <DropdownMenuTrigger
              render={
                <SidebarMenuButton
                  size="lg"
                  aria-label="Minha conta"
                  title="Minha conta"
                  className="data-popup-open:bg-sidebar-accent data-popup-open:text-sidebar-accent-foreground"
                />
              }
            >
              <Avatar nome={usuario.nome} className="bg-sidebar-primary text-sidebar-primary-foreground" />
              <div className="grid min-w-0 flex-1 leading-tight">
                <span className="truncate text-[13px] font-semibold text-sidebar-accent-foreground">
                  {usuario.nome}
                </span>
                <span className="truncate text-xs text-sidebar-muted">{perfil}</span>
              </div>
              <ChevronsUpDown className="ml-auto text-sidebar-muted" />
            </DropdownMenuTrigger>
            <DropdownMenuContent
              side={isMobile ? 'top' : 'right'}
              align="end"
              sideOffset={8}
              className="w-auto min-w-60"
            >
              <div className="flex items-center gap-2.5 px-1.5 py-1.5">
                <Avatar nome={usuario.nome} className="bg-primary text-primary-foreground" />
                <div className="grid min-w-0 leading-tight">
                  <span className="truncate text-sm font-semibold">{usuario.nome}</span>
                  <span className="truncate text-xs text-muted-foreground">{usuario.email}</span>
                  <span className="truncate text-xs text-muted-foreground">{perfil}</span>
                </div>
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setTrocandoSenha(true)}>
                <KeyRound />
                Trocar senha
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              {/* Trocar o tema não fecha o menu, para a pessoa ver a mudança e voltar se quiser */}
              <DropdownMenuGroup>
                <DropdownMenuLabel>Tema</DropdownMenuLabel>
                <DropdownMenuRadioGroup value={tema} onValueChange={(valor: Tema) => mudarTema(valor)}>
                  <DropdownMenuRadioItem value="claro">
                    <Sun />
                    Claro
                  </DropdownMenuRadioItem>
                  <DropdownMenuRadioItem value="dracula">
                    <Moon />
                    Dracula
                  </DropdownMenuRadioItem>
                </DropdownMenuRadioGroup>
              </DropdownMenuGroup>
              <DropdownMenuSeparator />
              {/* O menu só fecha com o logout confirmado, que recarrega a página no login */}
              <DropdownMenuItem closeOnClick={false} disabled={sair.isPending} onClick={() => sair.mutate()}>
                <LogOut />
                {sair.isPending ? 'Saindo…' : 'Sair'}
              </DropdownMenuItem>
              {sair.isError && (
                <p role="alert" className="max-w-60 px-1.5 py-1 text-xs text-destructive">
                  Não foi possível sair. Você continua conectado; tente de novo.
                </p>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </SidebarMenuItem>
      </SidebarMenu>
      <TrocaSenha aberto={trocandoSenha} aoMudar={setTrocandoSenha} />
    </>
  )
}

export default RodapeUsuario
