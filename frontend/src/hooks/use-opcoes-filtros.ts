import { useQuery } from '@tanstack/react-query'
import type { ClasseConsumo } from '@/config/classes'
import { apiFetch } from '@/lib/api/api-fetch'

// Formato de GET /api/filters/options combinado com o backend (docs/backend/impl_filtros.md)
export type OpcoesFiltros = {
  // Meses da base em ordem crescente, no formato yyyy-MM
  competencias: string[]
  municipios: { nome: string; bairros: string[] }[]
  classes: ClasseConsumo[]
  // Um alimentador pode atender mais de um município
  alimentadores: { codigo: string; municipios: string[] }[]
  // Códigos da Gold, ex.: "VEGETACAO". O nome na tela vem de src/config/causas.ts
  causas: string[]
}

// Ordem alfabética do português ("Água Fria" junto do A, e não depois do Z)
const ordemAlfabetica = new Intl.Collator('pt-BR').compare

function ordenar(opcoes: OpcoesFiltros): OpcoesFiltros {
  return {
    ...opcoes,
    municipios: opcoes.municipios
      .map(({ nome, bairros }) => ({ nome, bairros: [...bairros].sort(ordemAlfabetica) }))
      .sort((a, b) => ordemAlfabetica(a.nome, b.nome)),
  }
}

// As opções só mudam quando o pipeline roda: busca uma vez e guarda
export function useOpcoesFiltros() {
  return useQuery({
    queryKey: ['filtros', 'opcoes'],
    queryFn: async ({ signal }) => ordenar(await apiFetch<OpcoesFiltros>('/filters/options', { signal })),
    staleTime: Infinity,
  })
}
