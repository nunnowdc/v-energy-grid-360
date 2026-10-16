| ID            | Requisito                                                                 | Tipo        | Seção Doc | Responsável        | Status   |
| ------------- | ------------------------------------------------------------------------- | ----------- | --------- | ------------------ | -------- |
| REQ-DATA-01   | Ingestão de todos os arquivos na camada Bronze                            | Obrigatório | 3         | Agente Dados       | Pendente |
| REQ-DATA-02   | Camada Silver com dados confiáveis e tratamento de qualidade              | Obrigatório | 3         | Agente Dados       | Pendente |
| REQ-DATA-03   | Integridade referencial entre medição, faturamento e cadastro             | Obrigatório | 3         | Agente Dados       | Pendente |
| REQ-DATA-04   | Modelagem Gold baseada em perguntas de negócio                            | Obrigatório | 3         | Agente Dados       | Pendente |
| REQ-DATA-05   | Cálculo de DEC e FEC por alimentador (ANEEL)                              | Obrigatório | 3         | Agente Dados       | Pendente |
| REQ-DATA-06   | Exportação Gold para banco local                                          | Obrigatório | 3         | Agente Dados       | Pendente |
| REQ-DATA-07   | Orquestração via Databricks Workflow                                      | Obrigatório | 3         | Agente Dados       | Pendente |
| REQ-DATA-08   | Publicação de dicionário de dados da Gold                                 | Obrigatório | 3         | Agente Dados       | Pendente |
| REQ-DATA-09   | Testes de qualidade automatizados no pipeline                             | Diferencial | 3         | Agente Dados       | Pendente |
| REQ-PORTAL-01 | Dashboards de indicadores principais e comparação de períodos             | Obrigatório | 4         | Agente Portal      | Pendente |
| REQ-PORTAL-02 | Análise de variação de receita (Preço x Volume) por mun/bairro/classe     | Obrigatório | 4         | Agente Portal      | Pendente |
| REQ-PORTAL-03 | Visão 360 da UC (Histórico, faturas, medidor, GD, interrupções, chamados) | Obrigatório | 4         | Agente Portal      | Pendente |
| REQ-PORTAL-04 | Fila de unidades suspeitas ordenada por prioridade                        | Obrigatório | 4         | Agente Portal      | Pendente |
| REQ-PORTAL-05 | Gestão de ordens de inspeção (gerar, atualizar, registrar, cancelar)      | Obrigatório | 4         | Agente Portal      | Pendente |
| REQ-PORTAL-06 | Acompanhamento de DEC e FEC por alimentador                               | Obrigatório | 4         | Agente Portal      | Pendente |
| REQ-PORTAL-07 | Filtros e recortes de informação personalizados                           | Obrigatório | 4         | Agente Portal      | Pendente |
| REQ-PORTAL-08 | Exportação da fila de inspeção                                            | Diferencial | 4         | Agente Portal      | Pendente |
| REQ-PORTAL-09 | Upload de planilha de inspeções de campo                                  | Diferencial | 4         | Agente Portal      | Pendente |
| REQ-PORTAL-10 | Perfis de acesso por cargo                                                | Diferencial | 4         | Agente Portal      | Pendente |
| REQ-PORTAL-11 | Testes automatizados no backend                                           | Diferencial | 4         | Agente Portal      | Pendente |
| REQ-AI-01     | Agente Text-to-SQL para perguntas em português                            | Obrigatório | 5         | Agente IA          | Pendente |
| REQ-AI-02     | Tratamento de termos do dia a dia (ex: 'conta de luz')                    | Obrigatório | 5         | Agente IA          | Pendente |
| REQ-AI-03     | Trilha de auditoria das respostas da IA                                   | Obrigatório | 5         | Agente IA          | Pendente |
| REQ-AI-04     | Insights de IA integrados nas telas do portal                             | Obrigatório | 5         | Agente IA          | Pendente |
| REQ-AI-05     | Acesso ao agente diretamente no portal                                    | Obrigatório | 5         | Agente IA          | Pendente |
| REQ-AI-06     | Segurança: somente leitura e proteção contra prompt injection             | Obrigatório | 5         | Agente IA          | Pendente |
| REQ-AI-07     | Capacidade de follow-up (manutenção de contexto)                          | Diferencial | 5         | Agente IA          | Pendente |
| REQ-AI-08     | Avaliação automatizada da qualidade das respostas                         | Diferencial | 5         | Agente IA          | Pendente |
| REQ-DIAG-01   | Diagnóstico da variação de receita com causas sustentadas por dados       | Obrigatório | 6         | Agente Diagnóstico | Pendente |
| REQ-DIAG-02   | Recomendações acionáveis com ordem de grandeza do impacto                 | Obrigatório | 6         | Agente Diagnóstico | Pendente |
| REQ-DIAG-03   | Registro do diagnóstico na pasta docs/                                    | Obrigatório | 6         | Agente Diagnóstico | Pendente |
