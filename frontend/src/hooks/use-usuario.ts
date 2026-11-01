import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ehPerfil, permissoesPorPerfil, type Perfil, type Permissao } from '@/config/perfis'
import { apiFetch } from '@/lib/api/api-fetch'
import { ErroApi } from '@/lib/api/erro-api'
import { navegador, ROTA_LOGIN } from '@/lib/api/sessao'

// Resposta de GET /api/auth/me e de POST /api/auth/login
// (docs/backend/impl_autenticação-backend.md). O JWT vai só no cookie HttpOnly,
// que o navegador manda sozinho: o front nunca lê nem guarda o token
export type UsuarioApi = {
  id: string
  nome: string
  email: string
  perfil: string
}

export type Usuario = {
  id: string
  nome: string
  email: string
  perfil: Perfil
  permissoes: Permissao[]
}

export type Credenciais = {
  email: string
  senha: string
}

export const CHAVE_SESSAO = ['auth', 'me'] as const

function paraUsuario({ id, nome, email, perfil }: UsuarioApi): Usuario {
  // O banco só aceita os 5 perfis; outro valor seria um backend mais novo que o front
  if (!ehPerfil(perfil)) {
    throw new ErroApi(0, 'O seu perfil não é reconhecido pelo portal. Fale com a equipe de TI.')
  }
  return { id, nome, email, perfil, permissoes: permissoesPorPerfil[perfil] }
}

// null = ninguém logado. O 401 aqui é a resposta esperada para quem ainda não
// entrou, e não uma sessão expirada
async function buscarSessao(signal: AbortSignal) {
  try {
    return paraUsuario(await apiFetch<UsuarioApi>('/auth/me', { signal }))
  } catch (erro) {
    if (erro instanceof ErroApi && erro.status === 401) {
      return null
    }
    throw erro
  }
}

// Quem está logado. Só é buscado ao abrir o portal e trocado pelo login: a
// sessão que vence durante o uso aparece no 401 das outras consultas
// (lib/api/sessao.ts), que recarrega a página no login
export function useSessao() {
  return useQuery({
    queryKey: CHAVE_SESSAO,
    queryFn: ({ signal }) => buscarSessao(signal),
    staleTime: Infinity,
  })
}

// Para as telas da área logada, que só aparece com alguém logado (SessaoObrigatoria)
export function useUsuario() {
  const { data } = useSessao()
  if (!data) {
    throw new Error('useUsuario só funciona dentro da área logada')
  }
  const usuario = data

  function pode(permissao: Permissao) {
    return usuario.permissoes.includes(permissao)
  }

  return { usuario, pode }
}

export function useEntrar() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (credenciais: Credenciais) =>
      paraUsuario(await apiFetch<UsuarioApi>('/auth/login', { method: 'POST', corpo: credenciais })),
    onSuccess: (usuario) => {
      // Nada de outra conta fica no cache: o login pode ser de outra pessoa
      queryClient.removeQueries({ predicate: (consulta) => consulta.queryKey[0] !== CHAVE_SESSAO[0] })
      queryClient.setQueryData(CHAVE_SESSAO, usuario)
    },
  })
}

export function useSair() {
  return useMutation({
    mutationFn: async () => {
      try {
        await apiFetch<void>('/auth/logout', { method: 'POST' })
      } catch (erro) {
        // Sessão já vencida: o cookie não vale mais, então é só ir para o login
        if (!(erro instanceof ErroApi && erro.status === 401)) {
          throw erro
        }
      }
    },
    // Recarrega a página no login, o que apaga da memória os dados da conta
    // (cache das consultas e a conversa com o agente). Se o logout falhar (500,
    // rede), o cookie pode continuar valendo: a pessoa fica no portal e o menu
    // da conta mostra o erro (RodapeUsuario)
    onSuccess: () => navegador.abrir(ROTA_LOGIN),
  })
}
