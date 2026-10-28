// Mesmos valores da coluna role da tabela usuarios no backend
export type Perfil = 'DIRETORIA' | 'ATENDIMENTO' | 'PERDAS' | 'OPERACAO' | 'ADMIN_TI'

export type Permissao =
  | 'ver_indicadores'
  | 'ver_receita'
  | 'ver_visao_360'
  | 'ver_fila_inspecao'
  | 'ver_continuidade'
  | 'usar_agente_ia'

export const nomesPerfis: Record<Perfil, string> = {
  DIRETORIA: 'Diretoria',
  ATENDIMENTO: 'Atendimento',
  PERDAS: 'Perdas',
  OPERACAO: 'Operação',
  ADMIN_TI: 'Administrador (TI)',
}

// Espelho do mapa perfil → permissões do backend, que é a fonte da verdade.
// Só é usado pelo usuário de teste enquanto o login não existe.
// O agente de IA (painel ao lado das telas) é de todos os perfis (decisão do time)
export const permissoesPorPerfil: Record<Perfil, Permissao[]> = {
  DIRETORIA: ['ver_indicadores', 'ver_receita', 'ver_continuidade', 'usar_agente_ia'],
  ATENDIMENTO: ['ver_visao_360', 'usar_agente_ia'],
  PERDAS: ['ver_fila_inspecao', 'ver_visao_360', 'usar_agente_ia'],
  OPERACAO: ['ver_continuidade', 'usar_agente_ia'],
  ADMIN_TI: [
    'ver_indicadores',
    'ver_receita',
    'ver_visao_360',
    'ver_fila_inspecao',
    'ver_continuidade',
    'usar_agente_ia',
  ],
}

export function ehPerfil(valor: unknown): valor is Perfil {
  return typeof valor === 'string' && Object.hasOwn(permissoesPorPerfil, valor)
}
