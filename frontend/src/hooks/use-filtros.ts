import { useSearchParams } from 'react-router'
import { useOpcoesFiltros } from '@/hooks/use-opcoes-filtros'
import {
  aplicarFiltro,
  aplicarFiltros,
  lerFiltros,
  nomesFiltros,
  removerFiltros,
  type NomeFiltro,
} from '@/lib/filtros-url'

// Filtros da tela atual, guardados na URL: o link compartilhado abre com os
// mesmos filtros. Cada mudança é aplicada na hora, sem botão "Aplicar"
export function useFiltros() {
  const [params, setParams] = useSearchParams()
  const { data: opcoes } = useOpcoesFiltros()

  const filtros = lerFiltros(params, opcoes)
  const temFiltro = nomesFiltros.some((nome) => params.has(nome))

  // replace: trocar filtro não cria uma entrada nova no "Voltar" do navegador
  function alterarFiltro(nome: NomeFiltro, valor?: string) {
    setParams((atual) => aplicarFiltro(atual, nome, valor, opcoes), { replace: true })
  }

  // Vários de uma vez (ex.: começo e fim do período), numa troca só da URL
  function alterarFiltros(valores: Partial<Record<NomeFiltro, string | undefined>>) {
    setParams((atual) => aplicarFiltros(atual, valores, opcoes), { replace: true })
  }

  function limparFiltros() {
    setParams((atual) => removerFiltros(atual), { replace: true })
  }

  return { filtros, temFiltro, alterarFiltro, alterarFiltros, limparFiltros }
}
