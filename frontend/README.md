# Frontend

Aplicação web do portal V-Energy Grid 360: um sistema interno usado por atendentes, analistas e diretoria para consultar os dados consolidados da V-Energy.

## Stack

- [React](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/)
- [Vite](https://vite.dev/) (build e servidor de desenvolvimento)
- [React Router](https://reactrouter.com/) (navegação entre telas)
- [Tailwind CSS](https://tailwindcss.com/) v4 (estilos)
- [shadcn/ui](https://ui.shadcn.com/) com [Base UI](https://base-ui.com/) (componentes de interface)
- [Lucide](https://lucide.dev/) (ícones)
- [Inter](https://rsms.me/inter/) (tipografia)
- [TanStack Query](https://tanstack.com/query) (chamadas à API, cache e estados de carregamento)
- [Recharts](https://recharts.org/) pelo componente `chart` do shadcn/ui (gráficos)
- [react-markdown](https://github.com/remarkjs/react-markdown) com [remark-gfm](https://github.com/remarkjs/remark-gfm) (respostas do agente de IA em Markdown)

## Pré-requisitos

- Node.js 20 ou superior
- npm

## Como executar

Dentro da pasta `frontend/`:

```bash
npm install     # instala as dependências (só na primeira vez)
npm run dev     # sobe o servidor em http://localhost:5173
```

### Outros comandos

| Comando | O que faz |
|---|---|
| `npm run build` | Gera a versão de produção em `dist/` |
| `npm run preview` | Serve localmente a versão gerada pelo build |
| `npm run lint` | Verifica o código com o ESLint |
| `npm test` | Roda os testes automatizados uma vez |
| `npm run test:watch` | Roda os testes de novo a cada arquivo salvo |

## Padrão de organização

O projeto segue o **Page-Component Pattern**:

- **Páginas** (`src/pages/`): uma pasta por tela do portal. Montam a tela juntando componentes.
- **Componentes do projeto** (`src/components/`): uma pasta por componente criado pelo time (ex.: `AppHeader/`, `AppSidebar/`, `Layout/`).
- **Componentes do shadcn/ui** (`src/components/ui/`): componentes base (botão, input, tabela, modal…) adicionados pelo CLI do shadcn. Não seguem a regra de uma pasta por componente, porque é o CLI que cria os arquivos ali.
- **Configurações** (`src/config/`): definições usadas em mais de um lugar, como a lista de telas do menu (`navegacao.ts`).
- **Hooks** (`src/hooks/`): hooks reutilizáveis do React.
- **Utilitários** (`src/lib/`): funções auxiliares, como o `cn`, que combina classes do Tailwind.

```
src/
├── components/
│   ├── AppHeader/AppHeader.tsx
│   ├── AppSidebar/AppSidebar.tsx
│   ├── AvisoSazonalidade/AvisoSazonalidade.tsx ← aviso quando os períodos comparados cobrem meses diferentes do ano
│   ├── BlocoDados/BlocoDados.tsx          ← cartão com título e os 4 estados
│   ├── BotaoAgente/BotaoAgente.tsx        ← botão do cabeçalho que abre e fecha o agente de IA
│   ├── BuscaUc/BuscaUc.tsx                ← busca da UC pelo ID completo
│   ├── CabecalhoPagina/CabecalhoPagina.tsx ← título, descrição e filtros de cada tela
│   ├── CaixaPergunta/CaixaPergunta.tsx    ← campo da pergunta ao agente (Enter envia)
│   ├── CartaoKpi/
│   │   ├── CartaoKpi.tsx                  ← indicador com valor e variação
│   │   └── CartaoKpiEsqueleto.tsx
│   ├── ConsumoDozeMeses/ConsumoDozeMeses.tsx ← gráfico de consumo da UC (12 meses)
│   ├── ConversaAgente/ConversaAgente.tsx  ← perguntas e respostas, com espera e erro
│   ├── DetalheReceita/DetalheReceita.tsx  ← onde está a variação, descendo município › bairro › classe
│   ├── EstadoConsulta/EstadoConsulta.tsx  ← carregando, erro, vazio e atualizando
│   ├── EstadoErro/EstadoErro.tsx
│   ├── EstadoVazio/EstadoVazio.tsx
│   ├── FaturasEmAberto/FaturasEmAberto.tsx ← faturas pendentes e atrasadas da UC
│   ├── FeedbackResposta/FeedbackResposta.tsx ← 👍/👎 de uma resposta do agente
│   ├── FilaSuspeitas/FilaSuspeitas.tsx    ← fila de UCs suspeitas com motivos, energia e score
│   ├── FiltroSelect/FiltroSelect.tsx      ← um filtro (rótulo + lista)
│   ├── FiltrosGlobais/FiltrosGlobais.tsx  ← barra de filtros das telas
│   ├── GraficosMensais/GraficosMensais.tsx ← duas medidas por mês empilhadas, atual × anterior
│   ├── GrafoRaciocinio/GrafoRaciocinio.tsx ← caminho do agente: um nó por passo
│   ├── HistoricosUc/HistoricosUc.tsx      ← abas de faturas, leituras, interrupções e chamados
│   ├── Layout/Layout.tsx
│   ├── MarcaVEnergy/MarcaVEnergy.tsx      ← marca do portal (grade 3×3)
│   ├── MensagemAgente/MensagemAgente.tsx  ← resposta do agente com selo, tempo, 👍/👎 e o passo a passo
│   ├── MiniTendencia/MiniTendencia.tsx    ← barrinhas de tendência do KPI
│   ├── OrdensInspecao/OrdensInspecao.tsx  ← ordens geradas: enviar para campo, concluir, cancelar
│   ├── OcorrenciasPorCausa/OcorrenciasPorCausa.tsx ← barras das ocorrências por causa
│   ├── Paginacao/Paginacao.tsx            ← anterior/próxima com "1–10 de 48"
│   ├── PainelAgente/PainelAgente.tsx      ← agente de IA numa coluna à direita, ao lado da tela
│   ├── PassoAPasso/PassoAPasso.tsx        ← "Como a IA chegou nisso?": resumo, grafo, consulta e amostra
│   ├── PonteReceita/PonteReceita.tsx      ← cascata: receita base, efeitos e receita comparada
│   ├── RankingAlimentadores/RankingAlimentadores.tsx ← piores alimentadores em DEC
│   ├── ReceitaPorClasse/ReceitaPorClasse.tsx ← barras da receita de cada classe de consumo
│   ├── ResumoUc/ResumoUc.tsx              ← cadastro, medidor e geração própria da UC
│   ├── RotaInicial/RotaInicial.tsx
│   ├── RodapeUsuario/RodapeUsuario.tsx    ← usuário no rodapé do menu
│   ├── RotaProtegida/RotaProtegida.tsx
│   ├── SeloBandeira/SeloBandeira.tsx      ← bandeira tarifária com cor e nome
│   ├── SeloBase/SeloBase.tsx              ← período coberto pela base, no topo
│   ├── SeloConfianca/SeloConfianca.tsx    ← quanto dá para confiar na resposta do agente
│   ├── SeletorPeriodo/SeletorPeriodo.tsx  ← filtro de período: botão que abre um calendário de meses
│   ├── StatusPagamento/StatusPagamento.tsx ← paga, pendente ou atrasada, com ícone
│   ├── StatusOrdem/StatusOrdem.tsx        ← situação da ordem com ícone e texto
│   ├── SugestoesPerguntas/SugestoesPerguntas.tsx ← conversa vazia com exemplos de pergunta
│   ├── TabelaDecomposicao/TabelaDecomposicao.tsx ← receita dos dois períodos e os efeitos, por grupo
│   ├── TextoMarkdown/TextoMarkdown.tsx    ← resposta do agente em Markdown com o visual do portal
│   ├── Variacao/Variacao.tsx              ← ▲/▼ + sinal + número, sem cor
│   └── ui/                                ← shadcn/ui
├── config/
│   ├── bandeiras.ts         ← nome e cor de cada bandeira tarifária
│   ├── causas.ts            ← nome de cada causa de interrupção
│   ├── classes.ts           ← nome e cor de cada classe de consumo
│   ├── codigos.ts           ← categorias da Gold como texto de tela (com acento)
│   ├── motivos.ts           ← motivos da fila de inspeção como texto de tela
│   ├── navegacao.ts         ← telas do menu (grupo, título e descrição)
│   ├── nos-agente.ts        ← nome e função de cada um dos 12 nós do agente de IA
│   └── perfis.ts            ← perfis e permissões
├── hooks/
│   ├── use-agente-ia.ts       ← perguntar, auditoria e 👍/👎 do agente (rotas /api/ai/*, reais)
│   ├── use-continuidade.ts    ← DEC, FEC e ocorrências (GET /api/network/continuity)
│   ├── use-fila-inspecao.ts   ← fila de UCs suspeitas (GET /api/inspections/queue)
│   ├── use-filtros.ts         ← filtros da tela, guardados na URL
│   ├── use-indicadores.ts     ← KPIs da tela Indicadores (GET /api/metrics/general)
│   ├── use-mobile.ts
│   ├── use-opcoes-filtros.ts  ← opções dos filtros (GET /api/filters/options)
│   ├── use-ordens-inspecao.ts ← listar, gerar, mudar e cancelar ordens de inspeção
│   ├── use-receita.ts         ← efeito preço e volume (GET /api/metrics/revenue-variance, rota real)
│   ├── use-uc-360.ts          ← dados da UC (GET /api/uc/{id}/360)
│   └── use-usuario.ts         ← usuário atual (de teste até o login existir)
├── lib/
│   ├── api/
│   │   ├── api-fetch.ts     ← função única para chamar o backend
│   │   ├── erro-api.ts      ← erro com status e mensagem pronta para a tela
│   │   ├── query-client.ts  ← configuração do TanStack Query
│   │   └── sessao.ts        ← sessão expirada (401) leva ao login
│   ├── comparacao.ts        ← variação percentual entre dois períodos
│   ├── filtros-url.ts       ← ler e trocar filtros na URL
│   ├── formatacao.ts        ← moeda, número, percentual, kWh e datas no padrão brasileiro
│   ├── passos-agente.ts     ← passos da auditoria do agente viram os nós do grafo
│   ├── periodos.ts          ← regras dos períodos escolhíveis (tamanho, comparação, atalhos)
│   ├── tela-da-resposta.ts  ← tela e filtros do dashboard para uma resposta do agente
│   └── utils.ts
├── mocks/                   ← dados de exemplo (MSW), só no npm run dev
├── pages/
└── test/                    ← preparação dos testes e o renderizar()
```

### Regra geral de organização

- Tudo o que o time cria fica **dividido em arquivos pequenos, cada um com uma única responsabilidade**, para facilitar o debug e a edição.
- Cada página e cada componente tem **sua própria pasta**, com o mesmo nome do arquivo principal: `components/NomeDoComponente/NomeDoComponente.tsx`.
- Vale mesmo para componentes usados em um só lugar: o `AppHeader`, por exemplo, só é usado pelo `Layout`, mas tem a própria pasta.
- Arquivos específicos de um componente (tipos, testes) ficam dentro da pasta dele.
- **Nomes:** pastas e componentes em `PascalCase`; páginas terminam em `Page` (`ReceitaPage`); configurações, hooks e utilitários em minúsculas (`navegacao.ts`, `use-mobile.ts`).

Os estilos são escritos com classes do **Tailwind** direto no JSX. As cores e o tema ficam centralizados em variáveis CSS no `src/index.css`.

### Cores

| Uso | Variável | Classe do Tailwind |
|---|---|---|
| Cor principal (azul-petróleo): botões, links, menu ativo | `--primary` | `bg-primary`, `text-primary` |
| Classes de consumo (Residencial, Comercial, Industrial, Rural, Poder público) | `--chart-1` a `--chart-5` | `bg-chart-1`… |
| Período anterior nas comparações | `--chart-anterior` | `bg-chart-anterior` |
| Bandeiras tarifárias | `--bandeira-verde`, `--bandeira-amarela`, `--bandeira-vermelha-p1`, `--bandeira-vermelha-p2` | `bg-bandeira-verde`… |
| Fundo da área de conteúdo (cartões e cabeçalho ficam brancos sobre ele) | `--canvas` | `bg-canvas` |
| Coluna do agente de IA, um tom abaixo do canvas (balões e campo de pergunta ficam brancos sobre ela) | `--agente` | `bg-agente` |
| Menu lateral escuro em petróleo | `--sidebar`, `--sidebar-foreground`, `--sidebar-muted`… | `bg-sidebar`, `text-sidebar-muted`… |
| Marca (só na marca e no favicon) | `--marca-grade`, `--marca-energia` | `bg-marca-energia`… |

### Tipografia

- **Inter** (`font-sans`, o padrão) para todo o portal. É a fonte mais usada em painéis web e foi desenhada para telas.
- Números (KPIs, variações, tabelas) e códigos (UC, alimentador) na mesma fonte do texto, com a classe `tabular-nums`: todos os dígitos têm a mesma largura, então os valores ficam alinhados em coluna. O portal não usa fonte mono.

Regras:

- A cor de cada classe de consumo é sempre a mesma, em qualquer tela. Use `src/config/classes.ts` em vez de escrever a cor direto.
- As cores das bandeiras aparecem só em contexto de bandeira e sempre junto com o nome. Use `src/config/bandeiras.ts`.
- Variação (▲/▼) não tem cor: usa seta, sinal e número em cinza-escuro.
- Nunca use dois eixos Y no mesmo gráfico: empilhe dois gráficos que compartilham o eixo dos meses.
- Dois períodos no mesmo gráfico: o atual em petróleo (`--primary`) e o anterior em cinza (`--chart-anterior`), sempre com legenda e tooltip com os valores.
- Status (ex.: fatura atrasada) aparece com ícone e texto, nunca só com cor.
- Categorias da Gold vêm em maiúsculas e sem acento (ex.: `DANO ELETRICO`). Mostre com `textoDoCodigo()` de `src/config/codigos.ts`, que devolve "Dano elétrico". Palavra nova sem acento entra na lista desse arquivo.

### Imports

Use o alias `@/` para importar a partir de `src/`:

```tsx
import { Button } from '@/components/ui/button'
```

### Adicionar um componente do shadcn/ui

Dentro de `frontend/`:

```bash
npx shadcn@latest add <componente>
```

A lista de componentes está em https://ui.shadcn.com/docs/components.

## Telas e rotas

| Rota | Tela | Perfis com acesso | Objetivo |
|---|---|---|---|
| `/` | Indicadores | Diretoria, Administrador (TI) | Principais KPIs do negócio, comparados entre períodos |
| `/receita` | Receita | Diretoria, Administrador (TI) | Variação de receita (efeito-preço × efeito-volume) por município, bairro e classe |
| `/visao-360/:idUc` | Visão 360 | Atendimento, Perdas, Administrador (TI) | Tudo sobre uma unidade consumidora em uma única tela |
| `/inspecoes` | Fila de inspeção | Perdas, Administrador (TI) | Unidades suspeitas priorizadas e gestão das ordens de inspeção |
| `/continuidade` | Continuidade | Diretoria, Operação, Administrador (TI) | DEC e FEC por alimentador ao longo do tempo |

As rotas são definidas em `src/App.tsx` com o [React Router](https://reactrouter.com/), e a lista de telas do menu fica em `src/config/navegacao.ts`. Todas as telas são renderizadas dentro de `components/Layout`, que monta o menu lateral (`AppSidebar`), o cabeçalho (`AppHeader`) e o agente de IA (`PainelAgente`).

### Agente de IA

Não é uma tela: o botão **Agente de IA** do cabeçalho abre o agente numa coluna à direita, e a tela atual continua aberta e utilizável ao lado. Todos os perfis têm acesso (permissão `usar_agente_ia`).

- Em telas largas (a partir de 1024 px) o agente divide o espaço com a tela; nas estreitas, abre por cima.
- A conversa continua ao trocar de tela e ao fechar e reabrir o painel. "Nova conversa" começa outra sessão.
- Cada pergunta leva a tela aberta como contexto (`page`, e `id_uc` na Visão 360) e as 3 perguntas anteriores, para o agente entender "e em 2023?".
- Cada resposta mostra o selo de confiança, o tempo e o 👍/👎. O texto vem em Markdown (negrito, listas, tabelas) e é mostrado formatado; HTML no texto não é interpretado. **Ver o passo a passo** abre, dentro da própria resposta, o caminho que o agente percorreu: um nó por passo, com a consulta SQL e as primeiras linhas do resultado.
- **O dashboard acompanha a conversa.** Cada resposta com base (dados ou documentos; recusa e erro não contam) leva a tela para onde estão os dados dela: "faturamento em Recife" abre os Indicadores de Recife, "qual alimentador teve o maior DEC" abre a Continuidade naquele alimentador, "a UC mais suspeita" abre a Visão 360 dela. Quem escolhe é o agente, pela consulta que executou: as tabelas decidem a tela e o WHERE (ou a linha única do resultado) decide os filtros, no campo `dashboard` de `/api/ai/ask`. O front (`src/lib/tela-da-resposta.ts`) só aplica os valores que existem em `/filters/options` e que a tela tem. Respostas sem consulta (glossário, normas) abrem a tela do assunto da pergunta. A resposta mostra o link "No dashboard: …" para reabrir essa visão.

## Perfis de acesso

Cada usuário tem um perfil, e o perfil define as permissões (`ver_receita`, `ver_visao_360`…). O backend é a fonte da verdade. O frontend usa as mesmas permissões para esconder o que o usuário não pode usar:

- Telas sem permissão **não aparecem no menu**.
- Quem digita o endereço de uma tela sem permissão vê a tela **"Sem permissão"**.
- O `/` leva cada perfil para a primeira tela que ele pode abrir.

Os perfis usam os mesmos nomes da coluna `role` do backend: `DIRETORIA`, `ATENDIMENTO`, `PERDAS`, `OPERACAO` e `ADMIN_TI` (`src/config/perfis.ts`).

Enquanto o login não existe, o portal usa um **usuário de teste**. Para trocar o perfil dele, copie `.env.example` para `.env.local`, mude `VITE_PERFIL_TESTE` (ex.: `VITE_PERFIL_TESTE=DIRETORIA`) e reinicie o `npm run dev`.

## Chamadas à API

Toda chamada ao backend passa pela função `apiFetch` (`src/lib/api/api-fetch.ts`):

- Coloca o prefixo `/api`, envia o cookie de login e converte a resposta de JSON.
- Em caso de erro, lança um `ErroApi` com o `status` e uma mensagem em português, pronta para mostrar na tela.
- Desiste depois de 30 segundos. Quem precisa de mais tempo passa `tempoLimiteMs` (o agente de IA usa 90 s).
- **401** (sessão expirada): qualquer consulta ou alteração leva ao `/login` com o aviso "Sua sessão expirou. Entre novamente.". O JWT dura 15 minutos e não é renovado.
- **429** (limite de requisições): mostra "Muitas tentativas. Aguarde um instante e tente de novo." e não tenta de novo sozinho.

As telas não chamam o `apiFetch` direto: cada recurso tem um hook com o [TanStack Query](https://tanstack.com/query), em `src/hooks/use-<recurso>.ts`. O TanStack Query guarda o resultado em cache por filtro, cancela a busca anterior quando o filtro muda e entrega os estados `isPending`, `isFetching` e `isError` para a tela. Exemplo (ilustrativo):

```ts
// src/hooks/use-receita.ts
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api/api-fetch'

export function useReceita(municipio: string) {
  return useQuery({
    // A chave inclui os filtros: cada combinação tem o próprio cache
    queryKey: ['receita', municipio],
    queryFn: ({ signal }) =>
      apiFetch<RespostaReceita>(`/metrics/revenue-variance?${new URLSearchParams({ municipio })}`, { signal }),
    // Mantém o dado anterior na tela enquanto busca o do novo filtro
    placeholderData: keepPreviousData,
  })
}
```

Em desenvolvimento, o Vite repassa tudo o que começa com `/api` para o FastAPI em `http://127.0.0.1:8000` (veja `vite.config.ts`). Para as telas receberem dados, o backend precisa estar rodando, com as rotas registradas sob o prefixo `/api`.

No `npm run dev`, um botão flutuante do TanStack Query aparece no canto da tela. Ele mostra cada consulta, o cache e os erros. Esse botão não vai para o build de produção.

## Blocos de dados

Todo bloco que mostra dados do backend tem 4 estados, tratados pelo `EstadoConsulta`:

| Estado | Quando | O que aparece |
|---|---|---|
| Carregando | Primeira busca | Esqueleto no formato do bloco |
| Atualizando | O filtro mudou e o novo dado ainda não chegou | Dados anteriores esmaecidos |
| Erro | A busca falhou | Mensagem e botão "Tentar de novo", só dentro do bloco |
| Vazio | Não há dados para os filtros | "Nenhum dado para os filtros selecionados." |

Para gráficos e tabelas, use o `BlocoDados`, que já inclui o cartão com título. Os dados chegam pela função dentro do bloco, apenas quando existem:

```tsx
const receita = useReceita(filtros)

<BlocoDados
  titulo="Receita por mês"
  consulta={receita}
  estaVazio={(dados) => dados.meses.length === 0}
>
  {(dados) => <GraficoReceita meses={dados.meses} />}
</BlocoDados>
```

Para uma linha de indicadores, use o `EstadoConsulta` direto, com `CartaoKpi` e, no carregamento, `CartaoKpiEsqueleto`. Valores e percentuais são formatados com as funções de `src/lib/formatacao.ts`.

## Filtros

Os filtros ficam na URL, então um link compartilhado abre a tela com os mesmos filtros:

```
/continuidade?base_de=2025-01&base_ate=2025-06&municipio=Recife&alimentador=ALM-REC-001&causa=VEGETACAO
```

| Parâmetro | Formato | Sem o parâmetro |
|---|---|---|
| `base_de` e `base_ate` | Primeiro e último mês (`yyyy-MM`) do período base: de 1 a 24 meses, deixando espaço depois dele para o comparado | Indicadores e Continuidade: os 12 meses antes dos últimos 12. Receita: o primeiro ano da base. Sempre meses **da base**, nunca da data de hoje |
| `comparado_de` | Primeiro mês do período comparado. O tamanho é o do base, e ele começa depois do fim do base | Os mesmos meses do base no ano mais recente que cabe |
| `municipio` | Nome do município | Todos |
| `bairro` | Nome do bairro (exige `municipio`) | Todos |
| `classe` | `RESIDENCIAL`, `COMERCIAL`, `INDUSTRIAL`, `RURAL` ou `PODER_PUBLICO` | Todas |
| `alimentador` | Código do alimentador (ex.: `ALM-REC-001`) | Todos |
| `causa` | Código da causa na Gold (ex.: `VEGETACAO`); o nome na tela vem de `src/config/causas.ts` | Todas |

Filtros de cada tela, combinados com o backend em `docs/backend/impl_filtros.md`:

| Tela | Filtros |
|---|---|
| Indicadores | Período base, comparado com, município, classe |
| Receita | Período base, comparado com, município, bairro, classe |
| Fila de inspeção | Município, bairro, classe |
| Continuidade | Período base, comparado com, município, alimentador, causa |
| Visão 360 | Nenhum: a tela recebe o ID da UC |

As três telas com período usam os mesmos dois botões, "Período base" e "Comparado com", que abrem um calendário de meses (`SeletorPeriodo`): no base, clica no primeiro e no último mês (ou num atalho: anos jul–jun da base e anos civis); no comparado, só no primeiro mês, porque ele tem sempre o tamanho do base. Meses que não deixam espaço para a comparação ficam apagados. Escolher só o base leva o comparado para os mesmos meses do ano mais recente; com meses diferentes do ano (ex.: jan–mar × jul–set), a tela avisa que parte da variação pode ser da estação (`AvisoSazonalidade`). As regras ficam em `src/lib/periodos.ts`. Para a API, os Indicadores e a Continuidade mandam o comparado como `inicio` e `fim` e o base como `inicio_anterior` e `fim_anterior`; a Receita manda `inicio_p0`, `fim_p0`, `inicio_p1` e `fim_p1`. O alimentador depende do município: com um município escolhido, só aparecem os alimentadores que o atendem, e trocar para um município que ele não atende tira o alimentador da URL.

Cada tela escolhe quais filtros mostra com `<FiltrosGlobais campos={[...]} />` e lê os valores com o hook `useFiltros()`, que já descarta valores inválidos. Trocar o município limpa o bairro, e cada mudança é aplicada na hora. Cada filtro aceita um valor só.

A barra fica numa linha própria, abaixo do título da tela. Cada filtro tem largura fixa (definida em `FiltrosGlobais.tsx`), então escolher outro valor não muda o tamanho nem a posição dos filtros. Um valor maior que o filtro aparece cortado com "…" e inteiro ao passar o mouse. A lista de opções usa o `Select` do shadcn/ui, no visual do portal.

## Dados de exemplo (MSW)

Enquanto o backend não tem todas as rotas, o [MSW](https://mswjs.io/) responde com dados de exemplo **só no `npm run dev`**. Nada disso vai para o build de produção.

- Ligar e desligar: `VITE_USAR_DADOS_EXEMPLO=true` ou `false` no `.env.local`, e reiniciar o `npm run dev`.
- As respostas ficam em `src/mocks/handlers.ts`. As rotas sem exemplo seguem para o backend de verdade.
- Quando uma rota real ficar pronta, apague o handler dela.
- Os dados de exemplo **nunca** podem vir da base real (nomes, CPFs, endereços): use só valores inventados ou públicos.

Rotas com exemplo hoje (números inventados):

| Rota | Tela | Exemplo | Formato (proposta ao backend) |
|---|---|---|---|
| `GET /api/network/continuity` | Continuidade | `src/mocks/continuidade.ts` | `src/hooks/use-continuidade.ts` |

Nos testes (`npm test`) os exemplos respondem sem a demora simulada.

Rotas que já são reais e precisam do backend com a Gold no banco local (veja `backend/README.md`):

- `GET /api/filters/options`: as opções dos filtros. Os exemplos acima usam os municípios, bairros, classes, alimentadores e causas que ela devolve (`src/mocks/opcoes-atuais.ts`), então qualquer filtro escolhido na tela tem dados. Sem backend, e nos testes, usam as opções inventadas de `src/mocks/opcoes-filtros.ts`.
- `GET /api/metrics/general`: os Indicadores. Os testes deles usam números redondos inventados no próprio teste.
- `GET /api/metrics/revenue-variance`: a Receita. Os testes dela usam números redondos inventados no próprio teste.
- `GET /api/inspections/queue`, `GET /api/inspections/orders`, `POST /api/inspections/order`, `PATCH` e `DELETE /api/inspections/{id}`: a Fila de inspeção. As ordens ficam na tabela `ordens_inspecao`, que não vem com a Gold: crie uma vez com `backend/sql/ordens_inspecao.sql` (veja `backend/README.md`). Os testes da tela usam um backend inventado no próprio teste, com as mesmas regras (gerar é tudo ou nada; a hora vem em UTC).
- `GET /api/uc/{id}/360`: a Visão 360. Os testes dela usam os dados inventados de `src/mocks/uc-360.ts`.
- `POST /api/ai/ask`, `GET /api/ai/audit/{id}` e `POST /api/ai/feedback`: o Agente de IA. Além do backend, precisam das chaves do LLM no `backend/.env.local` (veja `backend/.env.example`); sem elas o agente responde em modo de teste. Os testes do painel usam respostas inventadas no próprio teste.

## Testes automatizados

Os testes usam o [Vitest](https://vitest.dev/) com a [Testing Library](https://testing-library.com/docs/react-testing-library/intro/), num navegador simulado (jsdom). Rode com `npm test`.

- **Onde ficam:** junto do que testam, com o mesmo nome e `.test` no fim. Exemplos: `components/EstadoConsulta/EstadoConsulta.test.tsx` e `lib/filtros-url.test.ts`.
- **O que cobrem hoje:**
  - menu e rotas por perfil;
  - o `apiFetch` (mensagens de erro, servidor fora do ar, tempo esgotado, busca cancelada);
  - a sessão expirada e as novas tentativas;
  - os 4 estados dos blocos;
  - a variação e o cartão de KPI;
  - os filtros na URL;
  - os formatos de número;
  - os dados de exemplo.
- **Componentes com consultas ou rotas:** renderize com o `renderizar()` de `src/test/renderizar.tsx`. Ele monta os mesmos provedores do portal (cache de consultas e rotas). A opção `opcoesFiltros` já deixa as opções dos filtros no cache, sem backend.
- **Preparação comum:** fica em `src/test/setup.ts`. Ele limpa a tela entre um teste e outro, adiciona os verificadores do jest-dom (`toBeInTheDocument`, `toBeDisabled`…) e simula o que o jsdom não tem.
- **Antes de abrir um PR:** `npm run lint`, `npm test` e `npm run build` devem passar.

## Montar uma tela

Toda tela começa com o `CabecalhoPagina`. Ele mostra o título e a descrição que estão em `src/config/navegacao.ts`, com espaço à direita para os filtros:

```tsx
function ReceitaPage() {
  return (
    <section className="flex flex-col gap-6">
      <CabecalhoPagina acoes={<FiltrosGlobais campos={['municipio', 'bairro', 'classe']} />} />
      {/* KPIs, gráficos e tabelas da tela */}
    </section>
  )
}
```

- **Nome e descrição da tela:** são escritos uma vez só, em `navegacao.ts`. Assim aparecem iguais no menu, na trilha do topo ("Negócio / Receita") e no título.
- **Grupo do menu:** cada tela fica em "Negócio" ou "Operação" (campo `grupo`). Um grupo sem nenhuma tela permitida para o perfil some do menu.
- **Fundo e cartões:** o fundo da área de conteúdo é cinza-claro (`bg-canvas`), e os blocos (`BlocoDados`, `CartaoKpi`) são cartões brancos sobre ele.
