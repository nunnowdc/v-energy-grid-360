import { nomesPerfis, permissoesPorPerfil, type Perfil } from '@/config/perfis'
import type { Usuario, UsuarioApi } from '@/hooks/use-usuario'

// DADOS DE EXEMPLO de GET /api/auth/me, para os testes. Contas inventadas,
// uma por perfil, com e-mails de domínio reservado para exemplos
export function usuarioApiExemplo(perfil: Perfil = 'ADMIN_TI'): UsuarioApi {
  const codigo = perfil.toLowerCase()
  return {
    id: `00000000-0000-4000-a000-${String(Object.keys(nomesPerfis).indexOf(perfil) + 1).padStart(12, '0')}`,
    nome: `Pessoa ${nomesPerfis[perfil]}`,
    email: `${codigo}@example.test`,
    perfil,
  }
}

export function usuarioExemplo(perfil: Perfil = 'ADMIN_TI'): Usuario {
  const { id, nome, email } = usuarioApiExemplo(perfil)
  return { id, nome, email, perfil, permissoes: permissoesPorPerfil[perfil] }
}
