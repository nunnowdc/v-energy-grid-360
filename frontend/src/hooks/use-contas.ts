import { useMutation } from '@tanstack/react-query'
import type { Perfil } from '@/config/perfis'
import type { UsuarioApi } from '@/hooks/use-usuario'
import { apiFetch } from '@/lib/api/api-fetch'

// Contas de acesso ao portal (docs/backend/impl_autenticação-backend.md):
//   POST  /api/auth/users    { nome, email, perfil, senha } → 201 com a conta criada.
//                            Só o ADMIN_TI; 409 = já existe conta com o e-mail
//   PATCH /api/auth/password { senha_atual, nova_senha } → 204, e a sessão continua.
//                            400 = senha atual errada
// O backend normaliza o e-mail (sem espaços, em minúsculas) e não lista as contas

// Mesmo mínimo do backend, na criação e na troca
export const TAMANHO_MINIMO_SENHA = 8

export type NovaConta = {
  nome: string
  email: string
  perfil: Perfil
  senha: string
}

export type TrocaSenha = {
  senhaAtual: string
  novaSenha: string
}

export function useCriarConta() {
  return useMutation({
    mutationFn: (conta: NovaConta) => apiFetch<UsuarioApi>('/auth/users', { method: 'POST', corpo: conta }),
  })
}

export function useTrocarSenha() {
  return useMutation({
    mutationFn: ({ senhaAtual, novaSenha }: TrocaSenha) =>
      apiFetch<void>('/auth/password', {
        method: 'PATCH',
        corpo: { senha_atual: senhaAtual, nova_senha: novaSenha },
      }),
  })
}
