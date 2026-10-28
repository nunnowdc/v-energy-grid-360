import {
  Activity,
  ClipboardList,
  LayoutDashboard,
  TrendingUp,
  UserRound,
  type LucideIcon,
} from 'lucide-react'
import type { Permissao } from '@/config/perfis'

// Grupos do menu lateral, na ordem em que aparecem
export const gruposNavegacao = ['Negócio', 'Operação'] as const

export type GrupoNavegacao = (typeof gruposNavegacao)[number]

export type ItemNavegacao = {
  to: string
  label: string
  // Frase que aparece abaixo do título da tela
  descricao: string
  icone: LucideIcon
  grupo: GrupoNavegacao
  permissao: Permissao
}

export const itensNavegacao: ItemNavegacao[] = [
  {
    to: '/',
    label: 'Indicadores',
    descricao: 'Principais indicadores do negócio, comparados entre períodos',
    icone: LayoutDashboard,
    grupo: 'Negócio',
    permissao: 'ver_indicadores',
  },
  {
    to: '/receita',
    label: 'Receita',
    descricao: 'Variação da receita entre períodos, separando efeito-preço e efeito-volume',
    icone: TrendingUp,
    grupo: 'Negócio',
    permissao: 'ver_receita',
  },
  {
    to: '/continuidade',
    label: 'Continuidade',
    descricao: 'DEC e FEC por alimentador ao longo do tempo',
    icone: Activity,
    grupo: 'Negócio',
    permissao: 'ver_continuidade',
  },
  {
    to: '/visao-360',
    label: 'Visão 360',
    descricao: 'Tudo sobre uma unidade consumidora em uma única tela',
    icone: UserRound,
    grupo: 'Operação',
    permissao: 'ver_visao_360',
  },
  {
    to: '/inspecoes',
    label: 'Fila de inspeção',
    descricao: 'Unidades suspeitas priorizadas e gestão das ordens de inspeção',
    icone: ClipboardList,
    grupo: 'Operação',
    permissao: 'ver_fila_inspecao',
  },
]

// A raiz "/" só fica ativa no endereço exato; as demais também valem
// para sub-rotas, como /visao-360/UC129001
export function estaAtivo(pathname: string, to: string) {
  if (to === '/') {
    return pathname === '/'
  }

  return pathname === to || pathname.startsWith(`${to}/`)
}

export function buscarItemAtual(pathname: string) {
  return itensNavegacao.find((item) => estaAtivo(pathname, item.to))
}

// Telas que o usuário pode abrir, na ordem do menu
export function itensPermitidos(permissoes: Permissao[]) {
  return itensNavegacao.filter((item) => permissoes.includes(item.permissao))
}
