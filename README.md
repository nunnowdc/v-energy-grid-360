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
