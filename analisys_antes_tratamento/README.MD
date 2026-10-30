# Análise Exploratória (EDA) — V-Energy Grid 360

Esta pasta contém somente a etapa de análise exploratória dos dados brutos.
Os scripts medem, agregam e visualizam as fontes; eles não limpam, alteram ou
transformam os arquivos da pasta `data/`.

> **Importante:** `data/` é somente leitura. Nenhum script da EDA grava nessa
> pasta.

## 1. Pré-requisitos

- Python 3.10 ou superior.
- Dados disponíveis em `data/`, na raiz do projeto.
- VS Code com as extensões Python e Jupyter, caso queira executar os notebooks.

Instale todas as dependências a partir da raiz do projeto:

```powershell
pip install -r requirements.txt
```

O arquivo inclui as bibliotecas de leitura e análise (`polars`, `pandas`,
`openpyxl`, `numpy` e `matplotlib`) e as ferramentas para notebooks
(`ipykernel`, `jupyter`, `nbconvert` e `jupytext`).

## 2. Estrutura esperada

```text
data/
├── leituras/
│   ├── leituras_2022.csv
│   ├── leituras_2023.csv
│   ├── leituras_2024.csv
│   ├── leituras_2025.csv
│   └── leituras_2026.csv
├── atendimentos.json
├── faturas.csv
├── geracao_distribuida.csv
├── inspecoes.xlsx
├── medidores.csv
├── ocorrencias_rede.csv
└── unidades_consumidoras.csv
```

Os scripts usam o helper compartilhado
[`analisys/scripts/analise_negocio/_helpers.py`](scripts/analise_negocio/_helpers.py).
Ele identifica a raiz pelo par `data/` + `analisys/`, usando o diretório atual
e o local do arquivo quando disponível. Assim, scripts e notebooks podem ser
executados a partir da raiz ou de qualquer subdiretório do projeto, sem
depender exclusivamente de `__file__`.

Os arquivos de entrada são resolvidos recursivamente dentro de `data/`.
Arquivos das fontes principais podem ficar diretamente em `data/`; os CSVs de
leituras são todos os arquivos cujo nome contém `leitura`, inclusive em
subdiretórios como `data/leituras/`. Ausências ou ambiguidades geram erros
explícitos com os caminhos considerados.

## 3. Fluxo de primeira execução

Em uma instalação nova, ou quando os dados foram alterados, execute os quatro
scripts de análise nesta ordem:

```powershell
python analisys/scripts/01_profiling.py
python analisys/scripts/02_integrity.py
python analisys/scripts/03_summary.py
python analisys/scripts/04_correlation.py
```

Depois, gere ou atualize todos os gráficos:

```powershell
python analisys/graficos/graficos_resultados.py
```

O mesmo fluxo pode ser executado pelos notebooks correspondentes em
`analisys/scripts/`, na ordem `01` a `04`.

## 4. Quando é possível executar somente os gráficos?

O script [analisys/graficos/graficos_resultados.py](graficos/graficos_resultados.py)
e o notebook [analisys/graficos/graficos_resultados.ipynb](graficos/graficos_resultados.ipynb)
não fazem o profiling das fontes. Eles leem os resultados JSON já produzidos:

- `analisys/resultados/perfil_bruto.json`;
- `analisys/resultados/integridade.json`;
- `analisys/summary_data.json`;
- `analisys/resultados/correlacoes.json`.

Portanto, é possível executar somente os gráficos quando esses quatro arquivos
existirem e estiverem atualizados. Isso é útil para apenas regenerar os PNGs.
Na primeira execução, ou após mudanças nos dados, rode antes os scripts `01`,
`02`, `03` e `04`.

Para verificar os arquivos antes de executar os gráficos:

```powershell
python -c "from pathlib import Path; b=Path('analisys'); arquivos=['resultados/perfil_bruto.json','resultados/integridade.json','summary_data.json','resultados/correlacoes.json']; [print(p, (b/p).exists()) for p in arquivos]"
```

## 5. O que cada etapa produz

| Etapa | Script | Saída principal |
|---|---|---|
| Profiling | `analisys/scripts/01_profiling.py` | `analisys/resultados/perfil_bruto.json` |
| Integridade | `analisys/scripts/02_integrity.py` | `analisys/resultados/integridade.json` |
| Summary | `analisys/scripts/03_summary.py` | `analisys/summary_data.json` |
| Correlação | `analisys/scripts/04_correlation.py` | `analisys/resultados/correlacoes.json` |
| Gráficos gerais | `analisys/graficos/graficos_resultados.py` | `analisys/graficos/resultados/*.png` |

### Profiling

Calcula linhas, colunas, tipos, nulos, duplicidades, distintos e valores
mínimo/máximo por fonte. Também registra informações sobre separador,
encoding e layout das leituras.

### Integridade

Calcula chaves órfãs entre as fontes, sem alterar os dados. Exemplos:
faturas sem UC correspondente e leituras sem medidor correspondente.

### Summary

Gera contagens agregadas por classe, município, bairro, tipo de medidor,
bandeira tarifária, status, tipo de ocorrência e evolução mensal das leituras.

### Correlação

Calcula Pearson e Spearman separadamente para cada fonte, sem fazer joins entre
tabelas. Identificadores (`id_*`, `cpf_cnpj`, `cep` e campos terminados em
`_id`) são excluídos. Valores textuais são convertidos para número quando
possível, e as falhas de conversão são registradas em `correlacoes.json`.

São gerados heatmaps com escala fixa de `-1` a `1`, valores anotados e número
de linhas utilizadas. As fontes com menos de duas variáveis numéricas elegíveis
são informadas e não geram matriz.

## 6. Notebooks

Os scripts `01_profiling.py`, `02_integrity.py`, `03_summary.py` e
`04_correlation.py` usam o formato percent: cada marcador `# %%` delimita uma
célula e pode ser executado pelo VS Code.

Para abrir um script como notebook no VS Code, abra o `.py` e use **Run Cell**.
Para gerar um arquivo `.ipynb` a partir do script:

```powershell
jupytext --to ipynb analisys/scripts/04_correlation.py --output analisys/scripts/04_correlation.ipynb
```

Ao criar uma nova análise, copie o bloco de inicialização dos scripts de
negócio (a busca de candidatos em `Path.cwd()` e `__file__`, quando existente)
e importe os helpers. Não use `os.path.dirname(__file__)` diretamente:

```python
from analisys.scripts.analise_negocio._helpers import (
    get_project_root, get_data_dir, resolve_data_file, resolve_readings_files
)

ROOT = get_project_root()
DATA_DIR = get_data_dir(ROOT)
leituras = resolve_readings_files(ROOT)
```

Em notebooks, `__file__` não existe; portanto, o padrão deve sempre permitir
que `get_project_root()` use o diretório de trabalho. O helper também fornece
`init_notebook()` para configurar o `sys.path` e os diretórios de saída sem
alterar o diretório de trabalho global.

Para executar e salvar as saídas:

```powershell
jupyter nbconvert --to notebook --execute --inplace analisys/scripts/04_correlation.ipynb
```

O notebook de gráficos executa o script de gráficos e exibe os heatmaps junto
com os demais gráficos, desde que os quatro JSONs de entrada existam:

```text
analisys/graficos/graficos_resultados.ipynb
```

## 7. Onde encontrar os resultados

- JSONs: `analisys/resultados/` e `analisys/summary_data.json`;
- PNGs: `analisys/graficos/resultados/`;
- Relatórios: `analisys/PERFIL.md`, `analisys/PANORAMA.md`,
  `analisys/SINTESE_EDA.md` e `analisys/PROGRESSO.md`.

## 8. Limitações conhecidas

- As leituras são consolidadas de vários arquivos anuais; o profiling por fonte
  pode refletir características específicas de cada arquivo, enquanto o total
  de linhas considera o conjunto consolidado.
- Correlações são descritivas e não indicam causalidade.
- Pearson pode ser influenciado por consumos negativos e outliers; por isso
  Spearman também é calculado.
- Faturas, leituras e outras fontes não são correlacionadas entre si sem um
  join explícito.
- Nulos, duplicidades, cabeçalhos incorporados, categorias não padronizadas e
  chaves órfãs são reportados para orientar a futura camada Silver; não são
  corrigidos pela EDA.

## 9. Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `Pasta 'data' não encontrada` | Comando executado fora do projeto ou dados ausentes | Execute a partir da raiz e confirme que `data/` existe |
| Gráficos faltando | Um dos quatro JSONs não existe ou está desatualizado | Rode os scripts `01` a `04` antes de `graficos_resultados` |
| Faturas aparecem com uma coluna | `faturas.csv` usa `;` como separador | O script detecta o separador; confirme o cabeçalho se o problema persistir |
| Categorias iguais ao nome da coluna | Cabeçalho repetido dentro dos dados | Investigue e trate na camada Silver |
| Muitos órfãos | Chaves com formatos diferentes ou universos distintos | Validar espaços, maiúsculas, zeros à esquerda e origem das fontes |
| Erro ao concatenar leituras | Layouts anuais diferentes | O script usa concatenação diagonal; registre as diferenças no profiling |
