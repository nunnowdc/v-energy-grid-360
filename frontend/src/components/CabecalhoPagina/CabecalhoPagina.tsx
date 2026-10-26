import type { ReactNode } from 'react'
import { useLocation } from 'react-router'
import { buscarItemAtual } from '@/config/navegacao'

type CabecalhoPaginaProps = {
  // Fica numa linha própria abaixo do título, ex.: a barra de filtros
  acoes?: ReactNode
}

// Título e descrição vêm da lista de telas (src/config/navegacao.ts),
// então o nome da tela é o mesmo no menu, na trilha e aqui
function CabecalhoPagina({ acoes }: CabecalhoPaginaProps) {
  const { pathname } = useLocation()
  const item = buscarItemAtual(pathname)

  if (!item) {
    return null
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">{item.label}</h1>
        <p className="text-sm text-muted-foreground">{item.descricao}</p>
      </div>
      {acoes}
    </div>
  )
}

export default CabecalhoPagina
