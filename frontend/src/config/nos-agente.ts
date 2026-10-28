// Os 12 nós do grafo do agente (ai-agent/src/grafo/construtor_grafo.py), pelo
// número que aparece nos passos da auditoria ("Nó 4 — Roteador: ...")
export const nosAgente: Record<number, { nome: string; funcao: string }> = {
  1: { nome: 'Filtro de segurança', funcao: 'Barra perguntas longas demais e tentativas de manipular a IA' },
  2: { nome: 'Contexto da conversa', funcao: 'Completa a pergunta com as anteriores quando ela depende delas' },
  3: { nome: 'Escopo', funcao: 'Confere se a pergunta é sobre os dados da V-Energy' },
  4: { nome: 'Roteamento', funcao: 'Decide se a resposta vem do banco, de documentos ou se é melhor recusar' },
  5: { nome: 'Busca em documentos', funcao: 'Procura no glossário e nas regras de negócio o que ajuda a responder' },
  6: { nome: 'Consulta certificada', funcao: 'Procura uma consulta pronta, já validada pelo time de dados' },
  7: { nome: 'Escrita da consulta', funcao: 'A IA escreve a consulta SQL sobre a base Gold' },
  8: { nome: 'Validação da consulta', funcao: 'Confere se a consulta só lê dados e usa tabelas permitidas' },
  9: { nome: 'Execução no banco', funcao: 'Roda a consulta na base Gold, com limite de tempo e de linhas' },
  10: { nome: 'Recusa honesta', funcao: 'Sem base segura para responder, a IA diz que não sabe' },
  11: { nome: 'Resposta final', funcao: 'Escreve a resposta e confere os números com os dados' },
  12: { nome: 'Auditoria', funcao: 'Registra a pergunta, a consulta, os passos e o tempo' },
}

export const NO_RECUSA = 10
export const NO_AUDITORIA = 12
