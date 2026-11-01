import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import type { ClasseConsumo } from '@/config/classes'
import type { StatusOrdem } from '@/hooks/use-ordens-inspecao'
import { apiBaixar, apiFetch } from '@/lib/api/api-fetch'
import type { Filtros } from '@/lib/filtros-url'

// GET /api/inspections/queue?municipio=&bairro=&classe=&pagina=&limite= (limite até 50; bairro
// só com município). Vem de fila_inspecao, na prioridade já calculada pela Gold.
// Sem nome e endereço do titular: para a fila bastam o ID e o bairro (LGPD)

export type ItemFila = {
  prioridade: number
  id_uc: string
  // 0 a 100 (v1 por regras, pesos ainda em calibração)
  score: number
  // Regras que dispararam, como vêm da Gold: "Queda de consumo >= 50% (+40); Medidor eletromecanico (+15)"
  motivo_suspeita: string
  kwh_recuperavel_estimado_ano: number
  municipio: string
  bairro: string
  classe: ClasseConsumo
  // Ordem do portal ainda não encerrada para esta UC (tabela do backend, não da Gold)
  ordem_aberta: { id_ordem: string; status: StatusOrdem } | null
}

export type FilaInspecao = {
  // Última competência usada no cálculo da fila (yyyy-MM-dd)
  data_referencia: string
  // Totais da fila inteira no recorte, não só da página
  resumo: { ucs: number; kwh_recuperavel_estimado_ano: number }
  pagina: number
  limite: number
  total: number
  itens: ItemFila[]
}

export const LIMITE_FILA = 20

function parametrosRecorte({ municipio, bairro, classe }: Filtros, params = new URLSearchParams()) {
  if (municipio) {
    params.set('municipio', municipio)
  }
  if (bairro) {
    params.set('bairro', bairro)
  }
  if (classe) {
    params.set('classe', classe)
  }
  return params
}

export function useFilaInspecao(filtros: Filtros, pagina: number) {
  const { municipio, bairro, classe } = filtros
  return useQuery({
    queryKey: ['fila-inspecao', municipio ?? null, bairro ?? null, classe ?? null, pagina],
    queryFn: ({ signal }) => {
      const params = parametrosRecorte(
        filtros,
        new URLSearchParams({ pagina: String(pagina), limite: String(LIMITE_FILA) }),
      )
      return apiFetch<FilaInspecao>(`/inspections/queue?${params}`, { signal })
    },
    // Ao trocar de página ou de filtro, a tabela anterior fica esmaecida até a nova chegar
    placeholderData: keepPreviousData,
    // A coluna "Ordem" muda quando alguém gera ou conclui uma ordem: busca de novo ao abrir a tela
    staleTime: 0,
  })
}

// GET /api/inspections/queue/export?municipio=&bairro=&classe= → .xlsx com a fila inteira do
// recorte (todas as páginas), com endereço e sem o nome do titular, para a equipe de campo
// progresso: porcentagem já baixada, ou undefined enquanto o servidor monta a planilha
export function useExportarFila(filtros: Filtros) {
  const [progresso, setProgresso] = useState<number>()
  const exportar = useMutation({
    mutationFn: async () => {
      setProgresso(undefined)
      const params = parametrosRecorte(filtros).toString()
      const { arquivo, nomeArquivo } = await apiBaixar(
        `/inspections/queue/export${params ? `?${params}` : ''}`,
        'fila-inspecao.xlsx',
        // A planilha pode ter milhares de linhas: dá mais tempo que uma consulta comum
        { tempoLimiteMs: 120_000, aoProgredir: setProgresso },
      )
      salvarArquivo(arquivo, nomeArquivo)
    },
  })
  return { ...exportar, progresso }
}

// O navegador só salva arquivo por um link com download: cria, clica e descarta
function salvarArquivo(arquivo: Blob, nome: string) {
  const endereco = URL.createObjectURL(arquivo)
  const link = document.createElement('a')
  link.href = endereco
  link.download = nome
  link.click()
  // Descartar na hora pode cancelar o download no Firefox e no Safari
  setTimeout(() => URL.revokeObjectURL(endereco))
}
