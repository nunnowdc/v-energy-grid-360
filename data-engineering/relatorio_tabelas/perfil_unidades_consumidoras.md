# Perfil de dados: `unidades_consumidoras.csv`

**Status:** parcial (faltam as saídas listadas na seção 5)
**Última atualização:** 20/10/2026
**Fonte:** `/Volumes/v-energy/raw_data/raw_data/unidades_consumidoras.csv` (CSV `,`, lido como texto)

---

## 1. Visão geral

| Item | Valor |
|---|---|
| Linhas no arquivo | 46.461 (46.460 de dados + 1 cabeçalho repetido) |
| Colunas (16) | id_uc, cpf_cnpj, nome_titular, logradouro, numero, bairro, municipio, uf, cep, classe, subgrupo_tarifario, alimentador, data_ligacao, status, latitude, longitude |
| `id_uc` distintos | 45.200 |
| **UCs reais** (sem os registros TESTE) | **45.000**, exatamente o número do case |

Conta: 46.460 linhas − 1.260 cópias de `id_uc` repetido = 45.200 ids distintos. Tirando os 200 TESTE, sobram 45.000.

---

## 2. Problemas encontrados

| # | Problema | Evidência | Tamanho |
|---|---|---|---|
| 1 | Cabeçalho repetido no meio do arquivo | Linha com `id_uc = "id_uc"` | 1 linha |
| 2 | **Registros de teste** | `id_uc` no padrão `TESTE0000` e todos com CPF `00000000000` | 200 linhas |
| 3 | Duplicatas exatas | Linhas 100% idênticas | 900 linhas |
| 4 | **Duplicatas conflitantes** | Mesmo `id_uc` com dados diferentes: 360 divergem em `nome_titular`, 40 também em `cpf_cnpj` | 360 UCs (investigação na seção 5) |
| 5 | **CEP com lixo** | `null` (161), só espaços (174), `NULL` (359), `N/A` (187), `-` (171), `9999-12-31` (169), `-1` (162) | ~1.383 linhas (3%) |
| 6 | Espaços sobrando | `logradouro` com espaço no início ou no fim | 2.797 linhas |
| 7 | UF em várias grafias | `PE`, `pe`, `Pernambuco`, `pernambuco`, `P.E.`, todas significando PE | 5.164 linhas fora do padrão `PE` |
| 8 | CPF/CNPJ em 4 formatos | 11 dígitos (36.260), 14 dígitos (5.601), máscara de CPF (4.031), máscara de CNPJ (568) | 4.599 linhas com máscara |
| 9 | Classe com caixa e acento variados | `residencial`/`Residencial`/`RESIDENCIAL`, `Poder Público`/`Poder Publico` | São 5 classes reais |
| 10 | **Encoding quebrado (mojibake) em `bairro`** | `InhamÃ£`, `BrasÃ­lia Teimosa`, `Ãguas Compridas`… Texto UTF-8 que foi lido como Latin-1 | **60 bairros, ~356 linhas.** Só a coluna `bairro` tem esse problema. |
| 11 | **Datas de ligação inválidas** | 92 datas entre 1900 e 1948, todas em `01/01`, seguidas de um buraco de 48 anos (nenhuma ligação entre 1949 e 1996). Nenhuma é de registro TESTE. | 92 linhas |

### Por que a célula 6 só encontrou 5 bairros com mojibake

A normalização troca `Ã` por `A` e remove os caracteres que não são letras. Com isso, `InhamÃ£` vira `INHAMA`, que é igual a `Inhamã` normalizado, e os dois caem no mesmo grupo. Já `BrasÃ­lia` vira `BRASALIA`, diferente de `BRASILIA`, e aparece como um bairro separado. A busca direta por `Ã` (célula 9b) mostra o tamanho real: 60 bairros.

### O que veio limpo

- `data_ligacao`: formato sempre `yyyy-MM-dd`, nenhuma data futura.
- `alimentador`: sempre `ALM-XXX-999`.
- `numero` e `subgrupo_tarifario`: formato consistente (falta ver a distribuição do subgrupo).
- Latitude e longitude: sempre numéricas, todas dentro da RMR, nenhuma invertida. Têm só 2 casas decimais, o que dá ~1 km de precisão: serve para mapa por bairro, não para rua.
- CEP válido (8 dígitos): todos começam com 50–56, ou seja, todos são de PE.
- `nome_titular`, `logradouro` e `municipio`: sem mojibake.

---

## 3. Tratamento proposto para a Silver

| # | Regra | Destino |
|---|---|---|
| 1 | Remover a linha com `id_uc = "id_uc"` | Descarte |
| 2 | Tirar os `id_uc` que não seguem `^UC[0-9]{6}$` | `silver_uc_quarentena`, motivo `REGISTRO_TESTE` |
| 3 | `dropDuplicates()` na linha inteira | Descarte |
| 4 | Duplicatas conflitantes: **critério pendente** (seção 5) | — |
| 5 | CEP: manter só os dígitos. É válido se tiver 8 dígitos e começar com 50–56. Caso contrário, vira `null` e `cep_valido = false`. | Silver |
| 6 | `trim` em **todas** as colunas de texto | Silver |
| 7 | UF: mapear as variantes conhecidas (`PE`, `PERNAMBUCO`, `P.E.`) para `PE`. Valor desconhecido gera flag, não é sobrescrito em silêncio. | Silver |
| 8 | CPF/CNPJ: só dígitos e nova coluna `tipo_pessoa` (`PF` com 11 dígitos, `PJ` com 14) | Silver |
| 9 | Classe: normalizar para `RESIDENCIAL`, `COMERCIAL`, `INDUSTRIAL`, `RURAL` e `PODER_PUBLICO` | Silver |
| 10 | Bairro: reparar o encoding **só nas linhas que contêm `Ã`**: `decode(encode(bairro, 'ISO-8859-1'), 'UTF-8')`. O reparo foi testado e funcionou nos 60 casos. | Silver |
| 11 | `data_ligacao` anterior a 1950: vira `null`, com `data_ligacao_invalida = true` | Silver |

**Cuidado com o reparo de encoding:** aplicar `encode`/`decode` num texto que já está correto (ex.: `Inhamã`) estraga esse texto. Por isso o reparo só pode rodar quando o valor contém `Ã`.

```python
F.when(F.col("bairro").contains("Ã"),
       F.decode(F.encode("bairro", "ISO-8859-1"), "UTF-8")).otherwise(F.col("bairro"))
```

---

## 4. O que o notebook atual (`bronze_to_silver.py`) já cobre

| # | Problema | Situação |
|---|---|---|
| 1 | Cabeçalho repetido | ✅ Trata |
| 2 | Registros TESTE | ❌ **Não trata.** Inflam a contagem de UCs e podem levar faturas de teste para a receita. |
| 3 | Duplicatas exatas | ✅ `dropDuplicates(["id_uc"])` resolve |
| 4 | Duplicatas conflitantes | ⚠️ Fica com uma versão aleatória |
| 5 | CEP | ❌ Não trata |
| 6 | Espaços | ❌ Não faz `trim` |
| 7 | UF | 🟡 Força `"PE"` em tudo. Funciona hoje, mas esconderia um erro novo. |
| 8 | CPF/CNPJ | ✅ Deixa só os dígitos (falta validar o tamanho e criar `tipo_pessoa`) |
| 9 | Classe | ✅ Trata |
| 10 | Mojibake em bairro | ❌ **Não trata.** Divide 60 bairros em dois na análise de receita por bairro. |
| 11 | Datas de 1900–1948 | ❌ Não trata |
| — | Coordenadas | ⚠️ `cast("double")` direto. Funciona com estes dados, mas no modo ANSI quebraria se viesse vírgula decimal. |

---

## 5. Pendências

- [ ] **Célula 8a**: as 360 divergências de nome e as 40 de CPF são só de escrita, ou são titulares diferentes? Isso define o critério de deduplicação.
- [ ] **Célula 8b**: ver a amostra dos registros TESTE.
- [ ] **Célula 6**: distribuição de `subgrupo_tarifario`, `status` e `municipio` (o case fala em 14 municípios).
- [ ] **Célula 7**: pivot classe × subgrupo (o esperado pelo case é Residencial = B1, Rural = B2, Comercial e Poder Público = B3, Industrial = A4) e o top de CPF/CNPJ com mais UCs.
- [ ] Na hora de analisar faturas e leituras, conferir se existem registros ligados aos 200 `id_uc` TESTE.

---

## 6. Observação para o diagnóstico de receita

Ligações por ano: cerca de 1.900 por ano entre 1998 e 2021. **De 2022 a 2026 foram só 372 no total** (56, 109, 104, 93 e 10), cerca de 0,8% da base, justamente no período das faturas.

Ou seja, praticamente não entraram UCs novas no período analisado. Isso contradiz em parte a frase do Diretor Comercial ("a base de clientes cresceu") e precisa ser cruzado com o `status` das UCs (ativas/desligadas) e com as faturas por mês. É candidata a hipótese no status report.
