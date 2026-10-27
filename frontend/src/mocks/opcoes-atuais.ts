import { bypass } from 'msw'
import type { OpcoesFiltros } from '@/hooks/use-opcoes-filtros'
import { opcoesFiltrosExemplo } from '@/mocks/opcoes-filtros'

let opcoes: Promise<OpcoesFiltros> | undefined

// Os dados de exemplo usam os municípios, bairros e classes que o backend devolve
// em GET /api/filters/options, para todo filtro escolhido na tela ter dados.
// Sem backend (e nos testes), usam as opções inventadas de src/mocks/opcoes-filtros.ts
export function opcoesAtuais() {
  opcoes ??=
    import.meta.env.MODE === 'test'
      ? Promise.resolve(opcoesFiltrosExemplo)
      : fetch(bypass('/api/filters/options'))
          .then((resposta) => (resposta.ok ? (resposta.json() as Promise<OpcoesFiltros>) : opcoesFiltrosExemplo))
          .catch(() => opcoesFiltrosExemplo)
  return opcoes
}
