# V-Energy Grid 360

Passo a passo para executar tudo.

## Como executar

### Frontend

Pré-requisito: Node.js 20 ou superior.

```bash
cd frontend
npm install
npm run dev
```

### Backend

Pré-requisito: Python 3.11 ou superior.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate # No Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m app.main
```

## Suposições e decisões do time

O que o time precisou decidir ou supor por conta própria, registrado aqui como o case pede. Os itens marcados com ⚠️ ainda estão em alinhamento.

### Perfis de acesso

| Perfil (`role`) | Quem usa | Telas |
|---|---|---|
| `DIRETORIA` | Diretoria, incluindo o diretor comercial | Indicadores, Receita, Continuidade |
| `ATENDIMENTO` | Atendentes do call center | Visão 360 |
| `PERDAS` | Gerente e analistas de perdas | Fila de inspeção, Visão 360 |
| `OPERACAO` | Gerência de operação | Continuidade |
| `ADMIN_TI` | Conta técnica da TI e dos desenvolvedores | Todas, mais a criação de contas |

- Diretor e diretor comercial usam o mesmo perfil, `DIRETORIA`.
- A Diretoria também vê a Continuidade, porque acompanha a qualidade do serviço, que gera multas regulatórias.
- Perdas também vê a Visão 360, para investigar a unidade consumidora suspeita.
- A Diretoria não vê a Visão 360 (dados pessoais de clientes) nem a Fila de inspeção (ações operacionais), seguindo a LGPD e o princípio do menor privilégio.
- `ADMIN_TI` não é um cargo do case: é uma conta técnica para administrar o portal.
- As contas são pré-cadastradas pelo `ADMIN_TI`, sem cadastro público. A troca de senha é opcional.
- O chat da IA fica disponível para todos os perfis e responde só com dados agregados, nunca com dados pessoais.

### Dados e telas

- **Receita:** compara o primeiro ano da base (jul/2022 a jun/2023) com os últimos 12 meses (jul/2025 a jun/2026), os dois períodos calculados na Gold. Os períodos aparecem só como texto, sem escolha livre no MVP.
- **Volume:** é o consumo medido nas leituras, porque as faturas não trazem kWh.
- **"Hoje":** é o último mês da base (jun/2026), nunca a data do computador.
- **Períodos:** Indicadores e Continuidade mostram os últimos 3, 6 ou 12 meses da base (padrão 12). Os Indicadores comparam com os mesmos meses imediatamente anteriores.
- **Gold:** no MVP, é um retrato fixo carregado no PostgreSQL local, sem atualização.
- **Decomposição preço × volume:** usa a fórmula publicada na Gold: efeito-volume = (kWh P1 − kWh P0) × preço P0, e efeito-preço = (preço P1 − preço P0) × kWh P1. A decomposição de Shapley do diagnóstico fica fora do MVP.
- **Filtros:** um valor por filtro. A Continuidade filtra por alimentador e causa: o município limita os alimentadores mostrados, e a causa filtra só as ocorrências. DEC e FEC são sempre do alimentador inteiro, nunca de um município ou de uma causa.
- ⚠️ **Motivo da suspeita:** a Fila de inspeção ainda não filtra por motivo, porque a Gold guarda vários motivos no mesmo texto. Depende de uma lista de motivos da Engenharia de Dados.
- **Dados de exemplo:** enquanto o backend não tem todas as rotas, o frontend usa dados de exemplo (MSW), só no `npm run dev`. Eles nunca vêm da base real (veja `frontend/README.md`).

## Fluxo de trabalho (Git Flow)

### Branches

| Branch | Função |
|---|---|
| `main` | Versão estável e entregável. Só recebe código vindo da `dev`. |
| `dev` | Integração do trabalho do time. Recebe as branches de task. |
| `feature/*`, `fix/*`, `refactor/*`, `docs/*` | Uma branch por task, sempre criada a partir da `dev`. |

```
feature/minha-task ──PR──► dev ──PR──► main
```

### Nomenclatura das branches de task

- `feature/<descricao>`: nova funcionalidade (ex.: `feature/camada-silver`)
- `fix/<descricao>`: correção de bug (ex.: `fix/calculo-dec-fec`)
- `refactor/<descricao>`: melhoria no código sem mudar o comportamento (ex.: `refactor/funcoes-limpeza-silver`)
- `docs/<descricao>`: documentação (ex.: `docs/dicionario-de-dados`)

Use letras minúsculas e hífens, sem espaços nem acentos.

### Passo a passo de uma task

1. Atualize a `dev` e crie a sua branch a partir dela:
   ```bash
   git checkout dev
   git pull
   git checkout -b feature/minha-task
   ```
2. Faça commits pequenos e descritivos:
   ```bash
   git add .
   git commit -m "Descreve o que foi feito"
   ```
3. Envie a branch para o GitHub:
   ```bash
   git push -u origin feature/minha-task
   ```
4. Abra um **Pull Request** de `feature/minha-task` para a **`dev`**.
5. Depois de aprovado, faça o merge e apague a branch da task.

### Regras de Pull Request

- Ninguém faz commit direto na `main` nem na `dev`: tudo entra via PR.
- Todo PR precisa de **no mínimo 2 aprovações** antes do merge.
- Quando a `dev` estiver estável, abre-se um PR da **`dev` para a `main`**, que segue a mesma regra de 2 aprovações.
- Antes de abrir o PR, atualize sua branch com a `dev` (`git pull origin dev`) e resolva eventuais conflitos.
