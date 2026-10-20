# Frontend

Aplicação web do portal V-Energy Grid 360: um sistema interno usado por atendentes, analistas e diretoria para consultar os dados consolidados da V-Energy.

## Stack

- [React](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/)
- [Vite](https://vite.dev/) (build e servidor de desenvolvimento)
- [React Router](https://reactrouter.com/) (navegação entre telas)

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

## Padrão de organização

O projeto segue o **Page-Component Pattern**:

- **Páginas** (`src/pages/`): uma por tela do portal. Montam a tela juntando componentes.
- **Componentes** (`src/components/`): partes reutilizáveis da interface (cards, tabelas, gráficos, menu).
- Cada página e componente fica em sua própria pasta, com o arquivo `.tsx` e o seu arquivo de estilo.

## Telas e rotas

| Rota | Tela | Público | Objetivo |
|---|---|---|---|
| `/` | Indicadores | Diretoria | Principais KPIs do negócio, comparados entre períodos |
| `/receita` | Receita | Diretor Comercial | Variação de receita (efeito-preço × efeito-volume) por município, bairro e classe |
| `/visao-360/:idUc` | Visão 360 | Atendimento | Tudo sobre uma unidade consumidora em uma única tela |
| `/inspecoes` | Fila de inspeção | Gerente de Perdas | Unidades suspeitas priorizadas e gestão das ordens de inspeção |
| `/continuidade` | Continuidade | Gerente de Operação | DEC e FEC por alimentador ao longo do tempo |

As rotas são definidas em `src/App.tsx` com o [React Router](https://reactrouter.com/). Todas as telas são renderizadas dentro de `components/Layout`, que contém o cabeçalho e o menu de navegação.

## Decisões em aberto

- Abordagem de estilos (CSS Modules, Tailwind etc.)
- Biblioteca para chamadas à API
