import {
  ehPerfil,
  nomesPerfis,
  permissoesPorPerfil,
  type Perfil,
  type Permissao,
} from '@/config/perfis'

export type Usuario = {
  nome: string
  perfil: Perfil
  permissoes: Permissao[]
}

// Usuário de teste enquanto o login não existe. Para testar outro perfil,
// defina VITE_PERFIL_TESTE no frontend/.env.local (veja o .env.example)
// Aceita minúsculas (ex.: "diretoria") para não quebrar .env.local antigos
const perfilDoEnv = String(import.meta.env.VITE_PERFIL_TESTE ?? '').toUpperCase()
const perfilTeste: Perfil = ehPerfil(perfilDoEnv) ? perfilDoEnv : 'ADMIN_TI'

const usuarioTeste: Usuario = {
  nome: `Teste ${nomesPerfis[perfilTeste]}`,
  perfil: perfilTeste,
  permissoes: permissoesPorPerfil[perfilTeste],
}

export function useUsuario() {
  const usuario = usuarioTeste

  function pode(permissao: Permissao) {
    return usuario.permissoes.includes(permissao)
  }

  return { usuario, pode }
}
