// Mesmos valores da coluna perfil da tabela usuarios no backend
export type Perfil = 'DIRETORIA' | 'ATENDIMENTO' | 'PERDAS' | 'OPERACAO' | 'ADMIN_TI'

export type Permissao =
  | 'ver_indicadores'
  | 'ver_receita'
  | 'ver_visao_360'
  | 'ver_fila_inspecao'
  | 'ver_continuidade'
  | 'usar_agente_ia'
  | 'ver_auditoria_ia'

export const nomesPerfis: Record<Perfil, string> = {
  DIRETORIA: 'Diretoria',
  ATENDIMENTO: 'Atendimento',
  PERDAS: 'Perdas',
  OPERACAO: 'Operação',
  ADMIN_TI: 'Administrador (TI)',
}

// Espelho do mapa de permissões do backend, que é quem decide de verdade.
// Aqui serve só para montar o menu, as rotas e os botões de cada perfil.
// O agente de IA (painel ao lado das telas) é de todos os perfis, mas o passo
// a passo de cada resposta (GET /api/ai/audit) é só do ADMIN_TI (decisão do time)
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
    'ver_auditoria_ia',
  ],
}

export function ehPerfil(valor: unknown): valor is Perfil {
  return typeof valor === 'string' && Object.hasOwn(permissoesPorPerfil, valor)
}
