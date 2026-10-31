# Planejamento de implementação — Autenticação e Autorização (RBAC)

## 1. Objetivo, fontes e estado atual

Este documento planeja a autenticação e a autorização do MVP **exclusivamente local** do V-Energy Grid 360 antes de `$to-spec`, `$to-tickets` e implementação. A [matriz de acesso e o modelo de contas](planejamento-backend.md#71-autenticação-e-matriz-de-autorização-dos-endpoints) são a fonte de verdade. A validação do Frontend de 31/10/2026 confirmou os contratos HTTP dos cinco endpoints e os fluxos de navegação e sessão descritos abaixo. Neste documento, **Aprovado** identifica uma decisão já tomada; **Proposta técnica** identifica detalhe ainda não homologado; **Dependência de integração** identifica trabalho de código futuro.

**Histórias atendidas:** o usuário de uma conta pré-cadastrada entra e vê somente as telas permitidas; altera a própria senha quando desejar; `ADMIN_TI` cria outras contas; cada endpoint aplica o perfil persistido. O backend decide o acesso efetivo, mesmo que o React oculte uma ação. Os dados analíticos e operacionais das cinco páginas permanecem sob seus contratos próprios.

**Estado observado na branch `dev` em 31/10/2026:** `backend/app/main.py` registra saúde, filtros, Indicadores, Receita, Visão 360, Fila de Inspeção, Continuidade e as quatro rotas de IA sob `/api`. `GET /api/network/continuity` foi integrado à `dev` pelo PR #67 e está disponível, mas ainda não possui RBAC; a proteção será aplicada na feature de Autenticação e Autorização para `DIRETORIA`, `OPERACAO` e `ADMIN_TI`. Não há controller de autenticação, tabela `usuarios` modelada em código, diretórios `entities/` e `security/`, nem proteção RBAC nas rotas. `app/core/database.py` reutiliza um engine SQLAlchemy 2 e fornece uma conexão por contexto; `app/core/config.py` já valida `DATABASE_URL` e origens CORS. O `ai_router` é importado de `ai-agent/` e requer atenção específica para aplicar o mesmo RBAC HTTP. O planejamento do banco por roles PostgreSQL não integra este MVP.

**Frontend observado:** `use-usuario.ts` usa `VITE_PERFIL_TESTE`; `LoginPage.tsx` ainda é informativa; `RotaProtegida.tsx` e `RotaInicial.tsx` usam o usuário simulado. `api-fetch.ts` chama `/api` com `credentials: 'same-origin'` pelo proxy Vite; `query-client.ts` e `sessao.ts` já redirecionam após `401`, mas precisam distinguir visita anônima inicial de sessão expirada. `MensagemAgente.tsx` oferece a gaveta de auditoria para todos os perfis, enquanto a política aprovada reserva seu endpoint a `ADMIN_TI`. A configuração atual do Vite ainda não contém `server.strictPort: true`. O runtime atual não inicializa MSW nem o declara como dependência; arquivos de dados simulados para testes permanecem no repositório. Essas observações descrevem o código, não uma mudança autorizada no frontend.

## 2. Escopo e arquitetura

**Aprovado:** `React → FastAPI (autenticação + RBAC) → Service → Repository → PostgreSQL`. O FastAPI controla método + rota por um mapa único de permissões em `security/`. O JWT identifica a conta; a cada requisição protegida o backend carrega o usuário e o `perfil` atual do banco antes de decidir. `ADMIN_TI` acessa todas as rotas protegidas e possui as rotas administrativas exclusivas. A equipe do backend protege as rotas FastAPI; a equipe de IA autoriza internamente as ferramentas do agente.

**Fronteiras:** Controller trata HTTP, cookies e schemas; Service trata login, hash, criação de conta e mudança de senha sem importar FastAPI; Repository executa SQL parametrizado com a conexão de `core/database.py`; Entity mapeia a tabela operacional; Schema é DTO HTTP; `security/` concentra assinatura/verificação do token e política RBAC, sem SQL próprio. Não criar modelos ORM para a Gold. Utilizar conexão PostgreSQL com privilégios mínimos suficientes às consultas da Gold e às operações aprovadas em tabelas operacionais, sem conta superusuária. A separação de credenciais para SQL gerado pela IA e auditoria permanece sob a integração com a equipe de IA, conforme o planejamento geral.

**Fora do escopo:** `SET LOCAL ROLE`, roles PostgreSQL por perfil no ciclo HTTP, RLS, cadastro público, recuperação de senha, refresh token, revogação de JWT, sessão persistida, Redis, serviços externos, proxy reverso adicional/HTTPS/infraestrutura de produção e uma tela administrativa nova. O proxy de desenvolvimento do Vite já existente permanece no fluxo local. Exportação/importação da Fila seguem futuras e sem paths definidos.

## 3. Tabela `usuarios`, entidade e persistência

**Modelo aprovado — exatamente uma tabela operacional `usuarios`:**

| Coluna | Tipo PostgreSQL aprovado | Restrição e uso |
| --- | --- | --- |
| `id` | `UUID` | Chave primária, gerada na criação. |
| `nome` | `VARCHAR(150)` | Obrigatória. |
| `email` | `VARCHAR(255)` | Obrigatória e única. |
| `senha_hash` | `VARCHAR(255)` | Obrigatória; contém somente hash Argon2id. |
| `perfil` | `VARCHAR(30)` | Obrigatória; domínio dos cinco perfis abaixo. |
| `criado_em` | `TIMESTAMP` | Obrigatória; data e hora reais da criação. |

Perfis: `DIRETORIA`, `ATENDIMENTO`, `PERDAS`, `OPERACAO`, `ADMIN_TI`. Persistir **`perfil`**, jamais `role`. Restrições de PK, `NOT NULL`, unicidade de email e domínio do perfil devem ser garantidas também no PostgreSQL. Não incluir `ativo`, `primeiro_acesso`, `ultimo_login`, colunas de token ou tabela de sessão. O tipo aprovado de `criado_em` é `TIMESTAMP`; sua eventual alteração para `TIMESTAMPTZ` exige decisão própria. A API proposta abaixo não expõe esse campo, evitando atribuir fuso não definido ao contrato.

**Entity:** mapear apenas as colunas aprovadas, com tipos e restrições compatíveis. **Repository:** buscar por email no login/bootstrap, buscar por UUID após validar JWT, inserir conta e atualizar apenas `senha_hash` da própria conta; usar transação para escritas e tratar conflito de unicidade. **Schemas:** separar entradas que contêm senha dos DTOs públicos; jamais serializar `senha_hash`. **Service:** validar regras de conta e orquestrar hash/verificação. **Normalização e validação sintática aprovadas para o MVP:** no cadastro e no login, remover espaços em branco no início e no fim do email e convertê-lo para letras minúsculas. Após normalizar, exigir `@` e no máximo 255 caracteres; buscar e persistir o valor normalizado, preservando a restrição de unicidade de `usuarios.email`. Não adicionar dependência específica para validar email nem aplicar outras regras de normalização.

A criação física da tabela será controlada por script SQL operacional próprio em etapa futura, sem DDL ao importar a API e sem alterar tabelas Gold. O bootstrap não cria a tabela: sua criação fará parte do processo de setup acordado entre Backend e Frontend. Não há migration ou SQL criado nesta etapa.

## 4. Bootstrap manual da primeira conta

**Aprovado:** script local, manual e idempotente, sugerido em `backend/scripts/bootstrap_admin_ti.py` (caminho técnico para validação). Pré-requisitos: tabela `usuarios` criada por procedimento controlado, conexão PostgreSQL configurada e senha inicial fornecida por quem executa. Preferir uma variável de ambiente informada somente na execução; o nome da variável será fechado na especificação. Não há senha fixa, senha de fallback nem endpoint HTTP de bootstrap.

O script procura primeiro `adminti.vgrid360@visagio.com` pelo email único. Se a conta já existir, encerra sem exigir uma nova senha e sem atualizar **qualquer** campo, inclusive senha e perfil. Se estiver ausente, exige uma senha inicial com **mínimo de 8 caracteres** antes da escrita e cria `nome=admin_ti`, `perfil=ADMIN_TI`, UUID novo, `criado_em` com a data/hora real da execução e somente hash Argon2id da senha. A verificação prévia e a restrição única do email protegem a idempotência mesmo em execuções concorrentes. Não imprimir senha, hash, token ou URL de conexão. Não criar tabela ou serviço adicional.

O bootstrap cria **somente a primeira conta `ADMIN_TI`**. Não criar automaticamente usuários demonstrativos; as demais contas serão cadastradas manualmente pelo administrador em `POST /api/auth/users`.

## 5. Senhas e identidade

**Aprovado:** senha mínima de 8 caracteres na criação e na troca; hash Argon2id na persistência; comparação da senha fornecida com o hash sem recuperar senha original; nenhuma exigência adicional de composição; nenhuma troca obrigatória no primeiro acesso. `PATCH /api/auth/password` exige autenticação e confirmação da senha atual, calcula hash novo e substitui `senha_hash`. Hashes, senhas e tokens nunca aparecem em respostas ou logs. Não há recuperação pública por email.

**Proposta técnica:** usar biblioteca Python mantida que ofereça Argon2id e verificação de hash e outra biblioteca mantida para JWT, ambas escolhidas e fixadas na implementação, sem implementações criptográficas próprias. O JWT assinado contém `sub` (UUID estável da conta), `iat` e `exp` (15 minutos). O algoritmo de assinatura é fixado pelo servidor; a verificação aceita somente o algoritmo configurado. O perfil **não é fonte de autorização no token**: a dependência carrega o usuário atual no PostgreSQL e usa seu `perfil`. Token válido cujo `sub` não corresponde a usuário retorna `401`. O segredo de assinatura vem de configuração local fora do Git; configuração ausente não deve gerar chave automática de desenvolvimento.

## 6. Cookie, sessão e navegação

**Aprovado:** JWT transportado **somente** no cookie `vgrid360_access_token`, com `HttpOnly=True`, `Secure=False`, `SameSite=Lax`, `Path=/` e expiração coerente com os 15 minutos do token. `Secure=False` vale apenas para HTTP local. Sem refresh, revogação ou sessão em banco. `Max-Age=900` segundos e `Expires` coerente são uma proposta técnica de serialização da expiração aprovada. O cookie `vgrid360_access_token` é definido por `Set-Cookie` no login e removido no logout com o mesmo nome e `Path=/`. Não retornar o JWT no JSON, não persistir token em `localStorage`/`sessionStorage` e não tentar lê-lo por JavaScript.

**Fluxo aprovado com o Frontend:** após credenciais corretas, responder `200` com os dados públicos do usuário e o cookie; o React estabelece o estado autenticado e carrega/atualiza `GET /api/auth/me`. Com caminhos relativos `/api/...` pelo proxy Vite, o navegador mantém a mesma origem e envia `vgrid360_access_token` com `credentials: "same-origin"` (também o padrão do `fetch`) nas chamadas protegidas; o FastAPI valida assinatura e expiração, consulta a conta e verifica a matriz. Em recarga, iniciar em **carregando**, consultar `/api/auth/me` e só então decidir entre tela autorizada e login. O `401` inicial leva a `/login` sem aviso; um `401` em rota protegida durante o uso limpa o cache e leva a `/login?motivo=sessao-expirada`. Não inferir autenticação a partir de perfil guardado no navegador.

**Logout:** somente usuário autenticado chama a rota; a resposta `204` remove o cookie `vgrid360_access_token`. O frontend limpa todas as queries que possam conter dados do usuário e navega para `/login`, inclusive se a chamada receber `401` porque o cookie já expirou. Isso não revoga cópias de JWT emitidas antes do logout: elas permanecem verificáveis até expirar. **Troca de senha aprovada para o MVP local:** após validar a senha atual e persistir novo hash Argon2id, a sessão atual permanece autenticada. O JWT existente conserva sua expiração original de 15 minutos; não se emite outro JWT apenas pela troca de senha. O logout encerra a sessão no navegador ao remover o cookie, sem revogar no servidor uma eventual cópia do token. Outros JWTs já emitidos podem continuar válidos até sua própria expiração; não há revogação nem encerramento automático de outras sessões. O frontend mostra sucesso e não exige novo login imediato.

## 7. Contratos HTTP aprovados com o Frontend

Os **métodos, paths, requests, respostas e status** dos cinco endpoints abaixo foram confirmados pelo Frontend. Os exemplos são ilustrativos e não contêm credenciais reais. O prefixo `/api` aparece uma única vez. Erros da aplicação usam `{"detail":"mensagem segura"}`; erros de validação HTTP do FastAPI podem manter a lista estruturada em `detail`. Detalhes de implementação ainda abertos estão identificados separadamente na seção 15.

### 7.1 `POST /api/auth/login`

| Campo | Contrato aprovado |
| --- | --- |
| Autenticação / perfis | Público; nenhum cookie prévio é exigido. |
| Request | JSON `{ "email": string, "senha": string }`. |
| Response | `200 OK` com `{ "id", "nome", "email", "perfil" }`, mais `Set-Cookie`; nunca JWT/hash no corpo. |
| Status | `200` sucesso; `401` credenciais inválidas; `422` request malformado; `503` PostgreSQL indisponível; `500` falha inesperada. |
| Efeitos / regras | Remove espaços em branco no início e no fim do email, converte-o para minúsculas e busca a conta pelo valor normalizado; verifica Argon2id e emite token de 15 minutos. Mesmo com cookie válido prévio, verifica as credenciais enviadas e substitui o cookie somente se forem válidas. A validação sintática mínima do email aprovada para o MVP está na seção 3. |

Request ilustrativo: `{ "email": "  Usuario@Example.Test  ", "senha": "<senha fornecida pelo usuário>" }`.

Response ilustrativa: `{ "id": "c66812f7-66a7-4464-a1e7-c74b27357b01", "nome": "Usuário de exemplo", "email": "usuario@example.test", "perfil": "ATENDIMENTO" }`.

Cookie ilustrativo no HTTP local: `Set-Cookie: vgrid360_access_token=<jwt>; Max-Age=900; Path=/; HttpOnly; SameSite=Lax`. O atributo `Secure` fica desativado para HTTP local; a forma exata de serializar a expiração segue como proposta técnica.

Resposta a credenciais inválidas: `401 { "detail": "Credenciais inválidas" }`, sem revelar se o email existe. A política de senha mínima é de criação/troca; login verifica a senha recebida contra a conta, sem transformar credencial incorreta em cadastro.

### 7.2 `POST /api/auth/logout`

| Campo | Contrato aprovado |
| --- | --- |
| Autenticação / perfis | Autenticado; cinco perfis. |
| Request | Sem corpo. |
| Response | `204 No Content`, com `Set-Cookie` expirando `vgrid360_access_token` no mesmo `Path=/` e sem JSON. |
| Status | `204` sucesso; `401` cookie ausente/inválido/expirado; `403` origem rejeitada; `500` falha inesperada. |
| Efeitos / regras | Remove o cookie do navegador; não revoga JWT no servidor. Após sucesso, chamadas protegidas sem outro token recebem `401`. |

Como o logout está aprovado como rota autenticada, um cookie já expirado recebe `401`; o frontend deve limpar seu estado local e navegar para login também nesse caso. A combinação exata de `Set-Cookie` em resposta `401` é detalhe a validar, sem depender dela para limpar o cache do React.

### 7.3 `GET /api/auth/me`

| Campo | Contrato aprovado |
| --- | --- |
| Autenticação / perfis | Autenticado; cinco perfis. |
| Request | Sem corpo; JWT no cookie `vgrid360_access_token`. |
| Response | `200 OK` com `{ "id", "nome", "email", "perfil" }`. |
| Status | `200` sucesso; `401` cookie ausente/inválido/expirado ou conta não encontrada; `503` banco indisponível; `500` falha inesperada. |
| Efeitos / regras | Recarrega a identidade e o perfil atuais do PostgreSQL; não retorna `senha_hash`. |

Response ilustrativa: `{ "id": "c66812f7-66a7-4464-a1e7-c74b27357b01", "nome": "Usuário de exemplo", "email": "usuario@example.test", "perfil": "ATENDIMENTO" }`.

### 7.4 `PATCH /api/auth/password`

| Campo | Contrato aprovado |
| --- | --- |
| Autenticação / perfis | Autenticado; cinco perfis; somente a própria conta identificada pelo JWT. |
| Request | JSON `{ "senha_atual": string, "nova_senha": string }`. |
| Response | `204 No Content`. |
| Status | `204` sucesso; `400` senha atual incorreta; `401` cookie ausente/inválido/expirado; `403` origem rejeitada; `422` request inválido ou nova senha curta; `503` banco indisponível; `500` falha inesperada. |
| Efeitos / regras | Verifica senha atual, grava novo hash Argon2id em uma transação; mantém `vgrid360_access_token` e o JWT já emitido até sua expiração original ou até o logout do navegador, sem emitir novo JWT. Outros JWTs emitidos não são revogados nem suas sessões encerradas automaticamente. |

Request ilustrativo: `{ "senha_atual": "<senha atual>", "nova_senha": "<nova senha com pelo menos 8 caracteres>" }`.

Erro aprovado: `400 { "detail": "Senha atual inválida" }`. O contrato não cria regra de proibir reutilização da senha anterior. A confirmação da nova senha ocorre somente no Frontend e não integra o request da API.

### 7.5 `POST /api/auth/users`

| Campo | Contrato aprovado |
| --- | --- |
| Autenticação / perfis | Autenticado; exclusivamente `ADMIN_TI`. |
| Request | JSON `{ "nome": string, "email": string, "perfil": Perfil, "senha": string }`. |
| Response | `201 Created` com `{ "id", "nome", "email", "perfil" }`, sem senha/hash/token. |
| Status | `201` sucesso; `401` cookie ausente/inválido/expirado; `403` perfil sem permissão ou origem rejeitada; `409` email já cadastrado; `422` campos/perfil/email inválidos ou senha com menos de 8 caracteres; `503` banco indisponível; `500` falha inesperada. |
| Efeitos / regras | Remove espaços em branco no início e no fim do email, converte-o para minúsculas e persiste o valor normalizado; gera UUID e `criado_em`, calcula hash Argon2id e persiste em transação. A unicidade do email normalizado e a restrição única do PostgreSQL resolvem também corridas entre requisições. Não há email de convite nem cadastro público. O cadastro poderá ser feito pelo Swagger ou por formulário administrativo que utilize este mesmo endpoint. |

Request ilustrativo: `{ "nome": "Usuária de exemplo", "email": "  Nova.Usuario@Example.Test  ", "perfil": "PERDAS", "senha": "<senha inicial com pelo menos 8 caracteres>" }`.

Response ilustrativa: `{ "id": "f2932a59-c10b-44ac-84e9-7b5211b03562", "nome": "Usuária de exemplo", "email": "nova.usuario@example.test", "perfil": "PERDAS" }`.

Conflito aprovado: `409 { "detail": "Email já cadastrado" }`, inclusive quando o email informado difere apenas em espaços nas pontas ou em letras maiúsculas/minúsculas. A validação sintática mínima de email aprovada para o MVP está registrada na seção 3, sem alterar a normalização já aprovada.

### 7.6 Regras transversais de erro

| Situação | Comportamento |
| --- | --- |
| Sem autenticação, token inválido ou expirado | `401` em rota protegida; novo login após expiração (**aprovado**). |
| Autenticado sem autorização do método + rota | `403` (**aprovado**). |
| JSON/campo inválido | `422` pelo FastAPI/Pydantic (**aprovado**; coerente com as rotas existentes). |
| Credenciais incorretas no login | `401` genérico (**aprovado**; o Frontend exibe erro no formulário, sem indicar sessão expirada). |
| Senha atual incorreta | `400` (**aprovado**; distinguir de JWT inválido). |
| Email duplicado | `409` (**aprovado**; capturar também violação concorrente de unicidade). |
| `Origin` presente e não autorizado em escrita autenticada | `403` (**aprovado**; manter a sessão). |
| Falha de PostgreSQL | `503` genérico sem detalhes de conexão (**aprovado no contrato dos endpoints**). |
| Erro inesperado | `500` genérico, sem SQL, credencial, hash, token ou stack trace (**aprovado quanto à não exposição**). |

## 8. Autorização centralizada e matriz de endpoints

**Aprovado:** uma dependência compartilhada extrai o cookie, valida o JWT, busca o usuário, obtém `usuarios.perfil` e consulta um mapa central indexado por **método HTTP + padrão de rota registrado**, não por uma string de URL arbitrária. O mapa nega por padrão qualquer rota protegida sem política explícita. `ADMIN_TI` recebe todas as rotas protegidas conhecidas e também as exclusivas; rotas públicas ficam fora da exigência de cookie. O controller aplica a dependência, sem `if perfil == ...` repetidos. A identidade enviada no corpo de `/api/ai/ask` não substitui a identidade autenticada; a propagação confiável ao módulo de IA requer alinhamento com essa equipe.

Legenda: `✓` permitido, `—` negado, `público` sem login. “Existente” significa rota registrada na branch examinada, **ainda sem RBAC**; “planejado” significa rota a implementar. A matriz reproduz as permissões aprovadas em `planejamento-backend.md`; a rota de Continuidade já está integrada à `dev`, e sua proteção RBAC permanece nesta feature.

| Método + endpoint | Estado atual | DIRETORIA | ATENDIMENTO | PERDAS | OPERACAO | ADMIN_TI |
| --- | --- | :---: | :---: | :---: | :---: | :---: |
| `POST /api/auth/login` | Planejado | público | público | público | público | público |
| `GET /api/health` | Existente | público | público | público | público | público |
| `GET /api/docs` | Existente | público | público | público | público | público |
| `GET /api/openapi.json` | Existente | público | público | público | público | público |
| `GET /api/redoc` | Existente | público | público | público | público | público |
| `POST /api/auth/logout` | Planejado | ✓ | ✓ | ✓ | ✓ | ✓ |
| `GET /api/auth/me` | Planejado | ✓ | ✓ | ✓ | ✓ | ✓ |
| `PATCH /api/auth/password` | Planejado | ✓ | ✓ | ✓ | ✓ | ✓ |
| `POST /api/auth/users` | Planejado | — | — | — | — | ✓ |
| `GET /api/filters/options` | Existente | ✓ | ✓ | ✓ | ✓ | ✓ |
| `GET /api/metrics/general` | Existente | ✓ | — | — | — | ✓ |
| `GET /api/metrics/revenue-variance` | Existente | ✓ | — | — | — | ✓ |
| `GET /api/uc/{uc_id}/360` | Existente | — | ✓ | ✓ | — | ✓ |
| `GET /api/network/continuity` | Existente nesta branch | ✓ | — | — | ✓ | ✓ |
| `GET /api/inspections/queue` | Existente | — | — | ✓ | — | ✓ |
| `GET /api/inspections/orders` | Existente | — | — | ✓ | — | ✓ |
| `POST /api/inspections/order` | Existente | — | — | ✓ | — | ✓ |
| `PATCH /api/inspections/{id}` | Existente | — | — | ✓ | — | ✓ |
| `DELETE /api/inspections/{id}` | Existente | — | — | ✓ | — | ✓ |
| `POST /api/ai/ask` | Existente | ✓ | ✓ | ✓ | ✓ | ✓ |
| `GET /api/ai/insights/{tela}/{entidade_id}` | Existente | ✓ | ✓ | ✓ | ✓ | ✓ |
| `POST /api/ai/feedback` | Existente | ✓ | ✓ | ✓ | ✓ | ✓ |
| `GET /api/ai/audit/{audit_id}` | Existente | — | — | — | — | ✓ |

Rotas futuras de importação/exportação da Fila permanecem previstas para `PERDAS` e `ADMIN_TI`, mas **sem método/path/contrato definidos** e sem linhas fictícias na matriz. `GET /api/health` e documentação não passam pela dependência RBAC. O acesso HTTP à auditoria detalhada da IA depende de aplicar a política inclusive ao roteador importado de `ai-agent/`; a autorização interna das tools permanece responsabilidade dessa equipe.

## 9. Matriz definitiva das cinco telas

| Tela | DIRETORIA | ATENDIMENTO | PERDAS | OPERACAO | ADMIN_TI |
| --- | :---: | :---: | :---: | :---: | :---: |
| Indicadores | ✓ | — | — | — | ✓ |
| Receita | ✓ | — | — | — | ✓ |
| Visão 360 | — | ✓ | ✓ | — | ✓ |
| Fila de Inspeção | — | — | ✓ | — | ✓ |
| Continuidade | ✓ | — | — | ✓ | ✓ |

O React usa o `perfil` de `GET /api/auth/me` para montar menu, redirecionamentos e ações, espelhando a matriz em `frontend/src/config/perfis.ts`. Após login ou recarga, prioriza a URL originalmente solicitada quando o perfil puder acessá-la; caso contrário, abre a primeira tela permitida: **DIRETORIA e ADMIN_TI → Indicadores; OPERACAO → Continuidade; ATENDIMENTO e PERDAS → Visão 360**. Uma visita a `/login` com sessão válida também leva à primeira tela permitida. Usuário anônimo vai ao login; usuário autenticado sem permissão vê “Sem permissão” sem disparar consultas da tela. Em recarga, `/auth/me` resolve o estado antes de renderizar conteúdo privado. Essa proteção visual melhora a experiência, mas a decisão final é do FastAPI.

## 10. Integração detalhada com o Frontend React

### 10.1 Login e carregamento inicial

O formulário futuro de `frontend/src/pages/Login/LoginPage.tsx` envia `email` e `senha` a `POST /api/auth/login` pelo caminho relativo `/api/auth/login`; o backend normaliza o email (remove espaços nas pontas e converte para minúsculas) antes da busca e devolve o cookie `HttpOnly` chamado `vgrid360_access_token` e os dados públicos `{ id, nome, email, perfil }`. O proxy Vite encaminha a chamada ao FastAPI, enquanto o navegador recebe e envia o cookie na origem do frontend. Em `401` por credenciais incorretas, o formulário mostra “E-mail ou senha incorretos.”, sem tratar o erro como expiração de sessão; `503/500` recebem mensagem genérica. Em sucesso, o cliente limpa o cache anterior, atualiza `/auth/me` e navega para a URL originalmente pedida, se autorizada, ou para a primeira tela permitida. Uma requisição `/auth/me` no início da aplicação ou após recarga deve distinguir **carregando**, **autenticado** e **não autenticado**; não renderizar menu nem dados privados enquanto a identidade estiver indefinida. `401` inicial leva silenciosamente a `/login`.

Exemplo de chamadas na mesma origem do navegador:

```ts
fetch("/api/auth/me", { credentials: "same-origin" })
fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" })
```

O login (`POST`) e a alteração de senha (`PATCH`) também usam caminhos relativos `/api/...` e `credentials: "same-origin"`. O logout apaga o cookie no navegador; a troca de senha mantém o cookie e a expiração original do JWT. Nenhuma dessas operações exige ler o cookie pelo JavaScript.

### 10.2 Hook de usuário, cache e navegação

Substituir o usuário constante de `frontend/src/hooks/use-usuario.ts` por consulta TanStack Query a `/auth/me`, preservando uma API de leitura de `usuario` e permissão para os componentes existentes. `frontend/src/config/perfis.ts` continua útil para nomes e navegação, mas seu mapa é apenas um espelho visual: não fornece autorização ao backend. `RotaProtegida.tsx` e `RotaInicial.tsx` precisam esperar a consulta antes de decidir; `AppSidebar.tsx`, `AppHeader.tsx`, `RodapeUsuario.tsx` e `Layout.tsx` passam a exibir o usuário real. Alteração de identidade após login/logout deve limpar ou invalidar o cache de **todas** as consultas sensíveis, inclusive IA e Visão 360; não conservar respostas da conta anterior. A `queryKey` de `/auth/me` deve ser própria e seu cache deve ser tratado separadamente da Gold estática.

`frontend/src/lib/api/query-client.ts` e `sessao.ts` já tratam `401` com navegação, mas precisam distinguir: `401` de `/auth/me` no carregamento inicial leva silenciosamente a `/login`; `401` de login mostra erro no formulário; qualquer `401` de rota protegida durante o uso limpa o cache e leva a `/login?motivo=sessao-expirada`, com “Sua sessão expirou. Entre novamente.”. `403` ao acessar uma tela exibe “Sem permissão” e impede as consultas da tela; `403` em operação mostra erro contextual no bloco ou em toast. Ambos preservam a sessão. Após `204` no logout, ou `401` por cookie já expirado nessa chamada, limpar todo o cache e ir a `/login`. Troca de conta também limpa todos os caches anteriores, inclusive IA e Visão 360. `frontend/src/lib/api/api-fetch.ts` já usa `credentials: "same-origin"` e caminhos relativos `/api`; manter esse padrão nas chamadas autenticadas, sem ler o cookie nem guardar JWT. O proxy de `frontend/vite.config.ts` mantém `/api` sob a origem do navegador. `credentials: "include"` só será necessário se, futuramente, o navegador chamar diretamente uma origem diferente, com CORS e atributos de cookie adequados.

### 10.3 Operações e IA

Alteração voluntária de senha pode ser oferecida em componente existente ou fluxo simples a acordar, sem presumir uma tela administrativa nova. O Frontend confirma a nova senha localmente, sem enviar campo de confirmação à API. Após a alteração, mostra sucesso e mantém a sessão até a expiração original do JWT ou o logout, sem novo token; outros JWTs já emitidos não são encerrados automaticamente. O `ADMIN_TI` pode criar contas pelo Swagger ou por um formulário administrativo que utilize `POST /api/auth/users`; não há obrigação de criar uma tela nova. O `409` por email duplicado aparece no campo de email; `400` por senha atual incorreta aparece no campo da senha atual. Em `frontend/src/components/MensagemAgente/MensagemAgente.tsx`, o botão “Como a IA chegou nisso?”, que abre `PassoAPasso`, deve aparecer somente a `ADMIN_TI`, pois `useAuditoriaAgente()` consulta `/api/ai/audit/{audit_id}`. Feedback e pergunta continuam disponíveis aos cinco perfis autenticados. O `user_id` enviado hoje pelo painel como `teste-...` não pode definir identidade real; a integração FastAPI–IA deve usar a identidade verificada do cookie e alinhar a interpretação do campo com a equipe de IA. Nenhuma mudança no contrato HTTP da IA é feita por este planejamento.

**Dependência de integração:** os JSON e os estados foram validados pelo Frontend. Assim que a Entrega 1 do Backend disponibilizar login, `/auth/me` e logout na branch compartilhada, o Frontend poderá substituir `VITE_PERFIL_TESTE` e a tela informativa de login, sem aguardar o RBAC geral. No estado local examinado, o MSW já não é iniciado em runtime nem consta nas dependências do frontend; permanecem arquivos de dados simulados usados em testes. A remoção do MSW em runtime integrou a `dev` com o PR #67 da Continuidade.

## 11. Segurança local, CORS e Origin

**Aprovado:** FastAPI e React executam localmente; o frontend utiliza caminhos relativos `/api` pelo proxy Vite e `credentials: "same-origin"`, que também é o padrão do `fetch`. Esse fluxo não depende de `credentials: "include"`. O cookie `vgrid360_access_token` mantém `HttpOnly=True`, `SameSite=Lax`, `Secure=False`, `Path=/` e expiração compatível com o JWT de 15 minutos. Usar um hostname consistente (`localhost` ou `127.0.0.1`) no navegador; `Secure=False` só é apropriado para HTTP local.

**CORS** controla chamadas do navegador a uma **origem diferente** da página. Manter `allow_credentials=True`, sem `*`, e permitir explicitamente as origens do frontend `http://localhost:5173` e `http://127.0.0.1:5173` quando houver acesso direto à API. Com o proxy Vite, as chamadas relativas `/api` são de mesma origem para o navegador e não exigem CORS. `credentials: "include"` só seria necessário em um futuro acesso direto a outra origem, junto com CORS e cookies configurados para esse fluxo.

**Validação de `Origin` nas operações que alteram estado** é uma verificação da origem da requisição recebida pelo FastAPI, distinta de CORS. A lista local aprovada para essa verificação contém `http://localhost:5173`, `http://127.0.0.1:5173` e `http://127.0.0.1:8000`. O navegador envia `Origin` em `POST`, `PATCH` e `DELETE` mesmo com o proxy Vite; o FastAPI deve aceitar as duas origens do frontend encaminhadas pelo proxy. A terceira origem permite operações diretas pelo Swagger UI em `http://127.0.0.1:8000/api/docs`. Essa lista pode compartilhar configuração com CORS, mas CORS e a validação de `Origin` exercem funções diferentes; a origem do Swagger não precisa de CORS quando chama a própria API na mesma origem. O Swagger permanece público como documentação, mas suas operações protegidas exigem login, cookie, JWT e RBAC; uma sessão obtida pelo frontend em `localhost` não deve ser presumida disponível no host `127.0.0.1`.

Quando `Origin` estiver presente em uma operação que altera estado, conferir a lista local e rejeitar origem não autorizada. Quando estiver ausente, aceitar a requisição para o MVP local **desde que** todas as demais verificações aplicáveis sejam satisfeitas; ausência de `Origin` não é falha de autenticação. Nas operações protegidas (`POST /api/auth/logout`, `PATCH /api/auth/password`, `POST /api/auth/users`, inspeções, feedback e outras já existentes), verificar JWT e RBAC independentemente de `Origin`: permitir a origem do Swagger não concede privilégio administrativo. `POST /api/auth/login` continua público, sem JWT ou RBAC prévio, mas `Origin` presente também deve pertencer à lista local. Aceitar ausência de `Origin` é uma simplificação aprovada e **não constitui proteção CSRF completa**; CORS e `HttpOnly` isoladamente tampouco eliminam CSRF. Não adicionar token CSRF, HTTPS, proxy reverso adicional ou infraestrutura externa por antecipação. Evitar senhas, hashes, JWT e strings de conexão em logs, exceções e exemplos.

**Porta de desenvolvimento do Frontend:** o Frontend planeja configurar `server.strictPort: true` em `frontend/vite.config.ts`. Assim, se a porta 5173 estiver ocupada, o Vite falhará claramente em vez de subir em 5174, que não integra a lista aprovada de `Origin`. A configuração ainda não consta no código local e pertence à integração do Frontend. `vite preview` na porta 4173 não faz parte deste fluxo local.

## 12. Arquivos sugeridos e responsabilidades

Nenhum arquivo de código é criado nesta etapa. Os nomes abaixo são **propostas técnicas** ajustáveis na especificação, respeitando as camadas existentes:

| Arquivo ou área futura | Responsabilidade |
| --- | --- |
| `backend/sql/usuarios.sql` | Criação controlada da tabela e restrições aprovadas, sem execução no import. |
| `backend/app/entities/user.py` | Mapeamento ORM de `usuarios` (somente esta tabela operacional). |
| `backend/app/schemas/auth.py` | Request/response Pydantic de login, usuário público, senha e criação de conta. |
| `backend/app/repositories/users.py` | Busca por email/UUID, inserção e atualização de `senha_hash` com SQLAlchemy e conexão existente. |
| `backend/app/services/auth.py` | Casos de uso de autenticação, criação e troca de senha; erros semânticos sem HTTP. |
| `backend/app/security/passwords.py` | Hash e verificação Argon2id. |
| `backend/app/security/tokens.py` | Emissão e validação de JWT de 15 minutos. |
| `backend/app/security/permissions.py` | Mapa único método + rota × perfis. |
| `backend/app/security/dependencies.py` | Dependência de identidade autenticada e verificação de permissão. A busca do usuário usa o repository, não SQL em `security/`. |
| `backend/app/controllers/auth.py` | Cinco rotas, cookies, validação HTTP, OpenAPI e tradução das respostas. |
| `backend/app/core/config.py`, `database.py`, `main.py` | Configuração de segredo/CORS, reutilização da conexão e registro único do router/handlers. |
| `backend/scripts/bootstrap_admin_ti.py` | Inicialização manual e idempotente, sem endpoint público. |
| `backend/tests/test_auth_*.py` | Testes unitários de política, HTTP, integração PostgreSQL e regressão. |

Não criar classes base, pasta vazia, segundo pool ou dependências além do necessário. Se um nome diferente se ajustar melhor aos padrões vigentes, preservar a responsabilidade e registrar a alteração na especificação.

## 13. Entregas conjuntas e critérios de conclusão

**Branch e responsabilidades aprovadas:** Pedro desenvolve `backend/` na branch compartilhada `feature/autenticacao`, incluindo modelo, endpoints, segurança, bootstrap, testes e as variáveis necessárias em `backend/.env.example`. Nunno desenvolve `frontend/`, incluindo login, sessão, navegação e tratamento de erros, e atualiza `setup.ps1`, `setup.sh` e `scripts/funcoes-setup.*` a partir dos contratos e nomes de variáveis comunicados por Pedro. Mudanças no `README.md` da raiz serão coordenadas; ninguém assume alterações nos arquivos da outra equipe sem alinhamento. O bootstrap não executa DDL: o script SQL da tabela pertence ao Backend e sua execução será incorporada ao setup acordado entre as equipes. Não versionar segredos.

| Entrega | Responsável e resultado verificável | Depende de | Critério para liberar a próxima entrega |
| --- | --- | --- | --- |
| **1. Autenticação básica** | **Pedro:** tabela `usuarios`, persistência, hash Argon2id, bootstrap manual e idempotente da primeira conta `ADMIN_TI`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`, JWT de 15 minutos, cookie `vgrid360_access_token` e testes HTTP/de segurança. | Script SQL da tabela e configuração local disponíveis; execução controlada do DDL antes do bootstrap, com integração ao setup acordada com Nunno. Variáveis documentadas em `backend/.env.example`. | Login público funciona; `/auth/me` e logout exigem autenticação; bootstrap não recria nem sobrescreve a conta; JWT, cookie, expiração e respostas de erro passam nos testes. Os três endpoints e os pré-requisitos/nomes das variáveis são comunicados ao Frontend na branch. **Ainda não aplicar RBAC geral às rotas de negócio existentes**, para não bloquear o Portal. |
| **2. Integração inicial do Frontend** | **Nunno:** tela de login, usuário obtido de `/api/auth/me`, logout, proteção de navegação, tratamento de `401`/`403`, limpeza de cache no logout/troca de conta, auditoria detalhada visível só a `ADMIN_TI` e `server.strictPort: true`. Usa proxy Vite, caminhos relativos `/api` e `credentials: "same-origin"`. | Entrega 1 disponível na mesma branch; variáveis e pré-requisitos de setup comunicados pelo Backend. | Login, recarga de sessão e logout funcionam com o backend real; navegação e tratamento de erros seguem os contratos validados. O frontend pode iniciar esta entrega imediatamente após a Entrega 1, sem esperar RBAC completo. |
| **3. Gerenciamento de usuários** | **Pedro:** `POST /api/auth/users` exclusivo de `ADMIN_TI` desde sua criação, por dependência de autorização reutilizável, e `PATCH /api/auth/password` para usuários autenticados; normalização/validação de email e senha, novos hashes Argon2id e testes de criação, troca e autorização. | Entrega 1; ocorre após a integração inicial do Frontend na sequência acordada. | Criação de contas dos cinco perfis, email único, confirmação da senha atual, sessão preservada e erros aprovados testados. O endpoint administrativo nunca fica acessível sem autenticação e autorização. |
| **4. RBAC completo** | **Pedro:** mapa central de permissões e dependências reutilizáveis no FastAPI; aplicar a matriz a todos os endpoints de negócio existentes, inclusive IA e Continuidade; `401` para falha de autenticação e `403` para perfil sem permissão. `GET /api/ai/audit/{audit_id}` fica exclusivo de `ADMIN_TI`, sem alterar as regras internas do agente. | Entregas 2 e 3, com login integrado e contas dos cinco perfis disponíveis para teste. | Testes parametrizados da matriz completa passam para os cinco perfis; rotas públicas seguem públicas. Esta é a última entrega funcional que restringe o acesso às rotas existentes. |
| **5. Validação conjunta** | **Pedro e Nunno:** testar uma conta de cada perfil, login/logout, `/auth/me`, JWT expirado, cookie HttpOnly, navegação, `401`/`403`, auditoria exclusiva, cadastro, alteração de senha, limpeza de cache e regressão das funcionalidades existentes. | Entregas 1–4 integradas na branch compartilhada. | Suítes e fluxos integrados aprovados; revisão concluída e **um único PR para `dev`** preparado. Não realizar merges parciais da feature. |

A sequência permite aprovações individuais das entregas. A Entrega 1 desbloqueia a integração inicial do Frontend; a Entrega 3 fornece as contas dos cinco perfis para validar a navegação e o RBAC; a Entrega 4 só restringe as rotas de negócio depois que o login está integrado. Os cinco contratos HTTP da seção 7 permanecem aprovados e inalterados. Endpoints ainda não implementados não devem ser anunciados como disponíveis antes de seus testes e registro no FastAPI.

## 14. Testes planejados e critérios de aceitação

Usar pytest/HTTPX nos contratos HTTP com overrides das dependências existentes; testar hash/JWT e política diretamente; testar persistência e restrições em **PostgreSQL isolado**, sem escrever no banco principal `v_energy` ou na Gold. Testes devem afirmar comportamento externo e limites de segurança, não apenas reproduzir a implementação.

- **Contas e bootstrap:** conta criada com UUID, `criado_em` real, perfil correto e hash Argon2id; nenhuma conta demonstrativa criada automaticamente; senha inicial com menos de 8 caracteres rejeitada; segunda execução preserva todos os dados; concorrência respeita email único; senha/hash não aparecem em logs/respostas.
- **Login e cookie:** credenciais corretas, incorretas e usuário inexistente; busca pelo email após remover espaços nas pontas e converter para minúsculas; validação sintática mínima aprovada (`@` e até 255 caracteres após normalizar); mensagem genérica; `401` de credenciais exibido no formulário, sem aviso de sessão expirada; `503/500` com mensagem genérica; cookie `vgrid360_access_token` com atributos/vida aprovados, JWT ausente do corpo; login com cookie prévio conforme contrato validado. Com o proxy Vite, `POST /api/auth/login` e `GET /api/auth/me` usam caminhos relativos e `credentials: "same-origin"`; verificar que o cookie emitido no login é enviado em `/auth/me` e nas demais chamadas protegidas.
- **JWT e sessão:** assinatura, `sub`, `iat`, `exp`; token adulterado, ausente, expirado, algoritmo inesperado ou `sub` sem usuário → `401`; troca de perfil no banco refletida em `/auth/me` sem depender de claim antigo; reload do frontend.
- **Logout e senha:** `204` sem corpo remove `vgrid360_access_token` e limpa o cache; `401` por cookie já expirado também leva o Frontend a limpar cache e voltar a `/login`; senha atual incorreta `400`; nova senha curta `422`; novo hash distinto; transação atômica; sessão atual preservada após troca sem novo JWT, com expiração original; outros JWTs já emitidos válidos até expirar; sem revogação.
- **Cadastro administrativo:** criação válida por `ADMIN_TI`, inclusive pelo Swagger; outros perfis `403`; email persistido sem espaços nas pontas e em minúsculas, com validação sintática mínima aprovada; email duplicado `409` mesmo após normalização, inclusive concorrência; perfil inválido e campos/senha inválidos `422`; `senha_hash` nunca serializado.
- **RBAC HTTP:** testes parametrizados para **cada método + endpoint** da matriz da seção 8, cruzados com os cinco perfis, `401` sem identidade e `403` para identidade sem permissão. Incluir Fila, Visão 360, Indicadores, Receita, Continuidade, filtros e as quatro rotas IA. Verificar autorização pelo padrão registrado para parâmetros de rota, sem abrir acesso por semelhança textual de URL. Rotas públicas permanecem acessíveis sem cookie.
- **CORS/Origin:** verificar separadamente CORS com origens explícitas do frontend e credenciais, sem wildcard, e a lista de `Origin` das escritas: `http://localhost:5173`, `http://127.0.0.1:5173` e `http://127.0.0.1:8000`. Cobrir `POST`, `PATCH` e `DELETE` com `Origin` do frontend permitido pelo proxy, operação autenticada pelo Swagger em `http://127.0.0.1:8000/api/docs` permitida, origem desconhecida rejeitada e ausência de `Origin` aceita no MVP local. Em todos os casos protegidos, exigir JWT/RBAC; `POST /api/auth/users` por perfil diferente de `ADMIN_TI` retorna `403` mesmo com `Origin` permitido, inclusive pelo Swagger.
- **Frontend e regressão:** estados carregando/anônimo/autenticado sem renderizar menu ou dados antes de `/auth/me`; URL originalmente solicitada quando autorizada e destinos padrão dos cinco perfis; `/login` com sessão válida; `401` inicial silencioso, `401` do login no formulário e `401` durante uso com redirecionamento a `/login?motivo=sessao-expirada`; `403` na tela sem consultas e `403` em operação com erro contextual, ambos sem logout; cache inteiro limpo no logout/troca de usuário, inclusive IA e Visão 360; ações administrativas; `GET /api/health`, filtros, Visão 360, Indicadores, Receita, Continuidade, inspeções e IA preservam contratos e só acrescentam a proteção aprovada. Na integração com o Frontend, conferir `server.strictPort: true` para evitar a porta 5174 fora das origens aprovadas.

## 15. Limitações e propostas pendentes

1. **Integração IA:** adaptar a borda HTTP do `ai_router` ao RBAC comum e à identidade verificada sem mudar silenciosamente os contratos da equipe de IA. O Frontend confirmou que restringirá o botão de auditoria a `ADMIN_TI`; a equipe de IA mantém sua autorização interna das ferramentas. O significado do `user_id` enviado hoje pelo painel ainda requer alinhamento entre equipes.
2. **Configuração:** escolher biblioteca/versão de Argon2id e JWT, nome da variável de segredo e da variável de senha do bootstrap durante `$to-spec`; não versionar segredos. A combinação exata de `Set-Cookie` em `401` no logout permanece detalhe técnico, sem impedir o Frontend de limpar o cache. Rate limiting e timeout continuam pendentes de dimensionamento, sem infraestrutura adicional presumida.
3. **Integração React e setup:** a Entrega 2 pode começar após a Entrega 1 do Backend, sem esperar o RBAC completo; retirar `VITE_PERFIL_TESTE`, integrar login/`/auth/me`/logout, navegação e limpeza de cache. Nunno atualizará `server.strictPort: true` e os scripts de setup após receber de Pedro os nomes das variáveis e os pré-requisitos do banco. A data de disponibilização da Entrega 1 e mudanças no `README.md` da raiz exigem coordenação entre as equipes. O MSW já não está ativo no runtime da `dev` após a integração do PR #67.
4. **Estado documental:** `planejamento-backend.md` já registra Continuidade como integrada à `dev` e os contratos HTTP de autenticação como validados pelo Frontend. Trechos históricos sobre períodos de Indicadores e Receita permanecem fora do escopo desta atualização.

## 16. Validação com a equipe do Frontend — concluída

- [x] Campos JSON e status dos cinco endpoints, incluindo `204` sem corpo no logout e na troca de senha; `400` para senha atual incorreta e `409` para email duplicado.
- [x] Cookie `vgrid360_access_token` com `HttpOnly=True`, `SameSite=Lax`, `Secure=False`, `Path=/` e expiração coerente com 15 minutos; Frontend não lê o cookie nem armazena JWT.
- [x] Envio de `email`/`senha`, login com sessão válida e primeira tela permitida conforme os cinco perfis.
- [x] Carregamento inicial por `/auth/me`, recarga e estados carregando/autenticado/anônimo.
- [x] Comportamentos distintos para `401` inicial, `401` de login, `401` por expiração e `403` em tela ou operação.
- [x] Caminhos relativos `/api` e `credentials: "same-origin"` pelo proxy Vite no login, `/auth/me`, logout e alteração de senha; `include` fica reservado a eventual chamada direta entre origens.
- [x] Lista de `Origin` aprovada: `http://localhost:5173`, `http://127.0.0.1:5173` e `http://127.0.0.1:8000`; origem desconhecida rejeitada e ausência aceita conforme a regra local, sem dispensar JWT/RBAC.
- [x] Navegação segundo os cinco perfis, URL originalmente solicitada quando autorizada e cache inteiro limpo no logout ou troca de conta.
- [x] Troca voluntária de senha: sessão atual preservada sem novo JWT e sem novo login; expiração original mantida.
- [x] Auditoria detalhada da IA visível somente para `ADMIN_TI`; pergunta e feedback disponíveis aos cinco perfis autenticados.
- [x] Acordada a retirada de `VITE_PERFIL_TESTE` e do usuário simulado quando os endpoints reais estiverem disponíveis; implementação futura.
- [x] Criação das demais contas pelo Swagger ou por formulário administrativo que use `POST /api/auth/users`; sem exigir tela nova.

**Próxima etapa, após aprovação deste documento:** transformar as decisões acordadas em especificação verificável. Esta validação documental não implementa endpoints, SQL ou alterações de frontend.
