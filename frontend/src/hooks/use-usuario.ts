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
const perfilTeste: Perfil = ehPerfil(import.meta.env.VITE_PERFIL_TESTE)
  ? import.meta.env.VITE_PERFIL_TESTE
  : 'admin_ti'

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
