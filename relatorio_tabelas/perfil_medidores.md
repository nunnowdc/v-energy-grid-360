# Perfil de dados: `medidores.csv`

**Status:** quase completo (faltam os itens da seção 6)
**Última atualização:** 20/10/2026
**Fonte:** `/Volumes/v-energy/raw_data/raw_data/medidores.csv` (CSV `,`, lido como texto)

---

## 1. Visão geral

| Item | Valor |
|---|---|
| Linhas | 51.812 (o case fala em ~52 mil) |
| Cabeçalho repetido / linhas vazias | 0 / 0 |
| Colunas (8) | id_medidor, id_uc, modelo, tipo, data_instalacao, data_retirada, data_ultima_manutencao, status |
| UCs com pelo menos 1 medidor | **45.000**: todas as UCs reais do cadastro |
| Status | ATIVO 45.445 · RETIRADO 6.367 |

Distribuição de medidores por UC (com as duplicatas incluídas): 1 medidor: 38.324 UCs · 2: 6.541 · 3: 134 · 4: 1.

---

## 2. Problemas encontrados

| # | Problema | Evidência | Tamanho |
|---|---|---|---|
| 1 | Duplicatas exatas | Pares 100% idênticos (ex.: MD500006, MD500081, MD501201). **Nenhuma duplicata conflitante:** nos ids repetidos, nenhuma coluna diverge. | Quantidade pendente (seção 6) |
| 2 | **`tipo` com grafias variadas** | `ELETRONICO` / `eletrônico` / `Eletronico`; `ELETROMECANICO` / `Eletromecanico` / `eletromecânico` / `ELETRO-MECANICO`; `SMART` / `Smart` / `smart meter` | 3 tipos reais. `ELETRO-MECANICO` = 606, `smart meter` = 443 |
| 3 | `modelo` com espaços sobrando | `"  EL-3000 "`, `" NX-700"` | 3.109 linhas |
| 4 | **`data_instalacao` em 4 formatos** | `yyyy-MM-dd` (48.084), `99-99-9999` (1.263), `dd/MM/yyyy` (1.249), `dd.MM.yyyy` (1.216) | 3.728 linhas (7,2%) fora do ISO |
| 5 | **O formato com traço parece ser MÊS-DIA-ANO** (americano), não dia-mês | Ver a seção 3 | ~1.263 linhas em risco |
| 6 | "Não retirado" representado de 2 jeitos | `null` (31.796) e a sentinela `9999-12-31` (13.649). Os dois somam 45.445, exatamente o total de ATIVO. | 13.649 sentinelas |
| 7 | **`data_ultima_manutencao` 100% vazia** | 51.812 nulos de 51.812 linhas | A coluna inteira |

### O que veio limpo

- `id_medidor` (sempre `MD999999`) e `id_uc` (sempre `UC999999`).
- `status` só tem 2 valores e **é coerente com a retirada**: todo ATIVO está sem data de retirada e todo RETIRADO tem uma.
- `data_retirada` está sempre em ISO, sem nenhuma data futura real. A primeira retirada foi em 2025-09-05.
- **Integridade com o cadastro:** todos os `id_uc` existem nas UCs, nenhum medidor está ligado a registro TESTE e nenhuma UC real ficou sem medidor.

---

## 3. Evidência de que o formato com traço é MM-dd-yyyy

O notebook do colega testa `dd-MM-yyyy` **antes** de `MM-dd-yyyy`. Se os valores com traço forem, na verdade, mês-dia, toda data em que o dia é ≤ 12 é lida com dia e mês trocados, sem nenhum aviso.

Duas evidências independentes apontam nessa direção:

**A) As "datas futuras".** Há 6 instalações em datas futuras, com máximo em `2026-12-03`. Ao mesmo tempo, a data de instalação mais comum da base é `2026-03-12` (57 medidores). `03-12-2026` lido como dia-mês dá 3 de dezembro (futuro). Lido como mês-dia dá 12 de março, a data mais comum.

**B) As "sobreposições" de medidores.** A célula 8 encontrou UCs com dois medidores ativos ao mesmo tempo. Em todos os 20 exemplos, a instalação do medidor novo é **a data de retirada do antigo com dia e mês trocados**:

| UC | Retirada do antigo (ISO, confiável) | Instalação do novo (como foi lida) |
|---|---|---|
| UC100948 | 2025-**12**-**07** | 2025-**07**-**12** |
| UC102867 | 2025-**11**-**05** | 2025-**05**-**11** |
| UC112215 | 2025-**10**-**09** | 2025-**09**-**10** |
| UC117554 | 2025-**11**-**07** | 2025-**07**-**11** |

Ou seja, na troca o medidor novo foi instalado **no mesmo dia** em que o antigo foi retirado. A data saiu errada porque foi lida como dia-mês. **As sobreposições não existem: são consequência do erro de leitura da data.**

Status: forte evidência. A confirmação final depende da célula 9 (seção 6).

### Sobre as 1.381 datas "ambíguas"

A célula 7 contou 1.381 datas em que dia e mês são ≤ 12. Isso é o esperado para datas aleatórias (cerca de 37% dos 3.728 valores fora do ISO). Nos formatos `/` e `.`, a convenção brasileira é dia-mês (ex.: `19/06/2000`, `20.04.2007`), então o risco real se concentra no formato com traço.

---

## 4. Tratamento proposto para a Silver

| # | Regra |
|---|---|
| 1 | `dropDuplicates()` (todas as duplicatas são exatas, então qualquer critério serve) |
| 2 | `tipo`: normalizar **sem acento e sem pontuação** antes de mapear para `ELETRONICO`, `ELETROMECANICO` e `SMART` |
| 3 | `trim` em `modelo` |
| 4 | `data_instalacao`: tentar ISO → `dd/MM/yyyy` → `dd.MM.yyyy` → **`MM-dd-yyyy`** (se a célula 9 confirmar) |
| 5 | `data_retirada`: transformar `9999-12-31` em `null` |
| 6 | `data_ultima_manutencao`: remover a coluna ou mantê-la documentada como "sem dados na fonte" |
| 7 | Validação automática: na troca de medidor, a instalação do novo deve ser igual à retirada do antigo. Isso serve de teste de qualidade, que é diferencial no case. |

---

## 5. O que o notebook atual (`bronze_to_silver.py`) já cobre

| # | Problema | Situação |
|---|---|---|
| 1 | Duplicatas exatas | ✅ `dropDuplicates(["id_medidor"])` resolve |
| 2 | Tipo | ❌ **Bug.** O mapeamento usa `upper().contains("ELETRON")` e `contains("ELETROMECAN")`. Só que `upper("eletrônico")` vira `"ELETRÔNICO"` e o `Ô` ≠ `O`, então não bate. O mesmo acontece com `"ELETROMECÂNICO"` e com `"ELETRO-MECANICO"` (por causa do hífen). **Sobram 6 categorias em vez de 3.** |
| 3 | Espaços em modelo | ❌ Não faz `trim` |
| 4 | Formatos de data | 🟡 Testa os 5 formatos, o que é bom |
| 5 | **Ordem dia/mês do formato com traço** | ❌ **Bug provável.** Testa `dd-MM-yyyy` antes de `MM-dd-yyyy`. Gera as datas futuras e as falsas sobreposições. |
| 6 | Sentinela `9999-12-31` | ✅ Transforma em `null` |
| 7 | Manutenção vazia | ⚪ Não trata, mas também não quebra nada |

---

## 6. Pendências

- [ ] Célula 4: número de linhas 100% idênticas e de `id_medidor` repetidos.
- [ ] Célula 8: número total de pares sobrepostos (os 20 exemplos sugerem que todos são do bug de data).
- [ ] Célula 9: confirmar o formato `MM-dd-yyyy`, cruzar modelo × tipo e ver o perfil da campanha de troca.

---

## 7. Achado para o diagnóstico de receita

**Houve uma campanha de troca de medidores entre setembro de 2025 e março de 2026.**

- Todas as 6.367 retiradas aconteceram nesse período (a primeira em 2025-09-05). Isso é cerca de 14% do parque.
- O ritmo foi de ~50 trocas por dia. As datas de instalação e de retirada mais frequentes são as mesmas (`2026-03-12`, `2025-09-23`, `2025-12-19`…).

**Por que importa:**
- **Volume:** medidor eletromecânico antigo costuma registrar menos que o real. Se a troca foi para eletrônico ou smart, o consumo medido dessas UCs deve **subir** depois da troca. Se cair, vale investigar.
- **Perdas:** uma UC cujo consumo dispara depois da troca é sinal de que o medidor antigo estava com defeito ou adulterado. Esse sinal pode entrar na fila de inspeção.
- **Período do diagnóstico:** a campanha cai dentro dos "últimos 12 meses" que o Diretor Comercial compara com o primeiro ano.

A confirmar com as leituras: comparar o consumo antes e depois da troca.
