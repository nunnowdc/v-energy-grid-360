export type Perfil = 'diretoria' | 'atendimento' | 'perdas' | 'operacao' | 'admin_ti'

export type Permissao =
  | 'ver_indicadores'
  | 'ver_receita'
  | 'ver_visao_360'
  | 'ver_fila_inspecao'
  | 'ver_continuidade'

export const nomesPerfis: Record<Perfil, string> = {
  diretoria: 'Diretoria',
  atendimento: 'Atendimento',
  perdas: 'Perdas',
  operacao: 'Operação',
  admin_ti: 'Administrador (TI)',
}

// Espelho do mapa perfil → permissões do backend, que é a fonte da verdade.
// Só é usado pelo usuário de teste enquanto o login não existe.
export const permissoesPorPerfil: Record<Perfil, Permissao[]> = {
  diretoria: ['ver_indicadores', 'ver_receita', 'ver_continuidade'],
  atendimento: ['ver_visao_360'],
  perdas: ['ver_fila_inspecao', 'ver_visao_360'],
  operacao: ['ver_continuidade'],
  admin_ti: [
    'ver_indicadores',
    'ver_receita',
    'ver_visao_360',
    'ver_fila_inspecao',
    'ver_continuidade',
  ],
}

export function ehPerfil(valor: unknown): valor is Perfil {
  return typeof valor === 'string' && Object.hasOwn(permissoesPorPerfil, valor)
}
