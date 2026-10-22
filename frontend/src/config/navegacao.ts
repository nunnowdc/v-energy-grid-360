import {
  Activity,
  ClipboardList,
  LayoutDashboard,
  TrendingUp,
  UserRound,
  type LucideIcon,
} from 'lucide-react'

export type ItemNavegacao = {
  to: string
  label: string
  icone: LucideIcon
}

export const itensNavegacao: ItemNavegacao[] = [
  { to: '/', label: 'Indicadores', icone: LayoutDashboard },
  { to: '/receita', label: 'Receita', icone: TrendingUp },
  { to: '/visao-360', label: 'Visão 360', icone: UserRound },
  { to: '/inspecoes', label: 'Fila de inspeção', icone: ClipboardList },
  { to: '/continuidade', label: 'Continuidade', icone: Activity },
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
