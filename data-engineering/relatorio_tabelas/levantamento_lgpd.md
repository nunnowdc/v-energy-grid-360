# Levantamento LGPD: dados pessoais no pipeline V-Energy Grid 360

**Data:** 26/10/2026
**Escopo:** as 8 fontes brutas e as camadas Bronze, Silver e Gold, mais os destinos previstos (CSV, banco local, portal, agente de IA, repositório GitHub).

> Este é um mapeamento técnico de riscos, não um parecer jurídico. As referências à LGPD (Lei 13.709/2018) indicam onde cada ponto se encaixa; a decisão final sobre bases legais e contratos é do jurídico.

---

## 1. Resumo

- **Não há dados pessoais sensíveis** no sentido do art. 5º, II (origem racial, saúde, religião, biometria etc.).
- **Há muitos dados pessoais** (art. 5º, I): nome, CPF, endereço e tudo o que se liga a eles pelo `id_uc`: consumo, faturas, chamados e inspeções.
- **Os 3 conjuntos de maior dano num vazamento:**
  1. **Cadastro** (nome + CPF + endereço): permite identificação direta e fraude de identidade.
  2. **Inspeções e fila de perdas**: associam uma pessoa identificável a **suspeita ou confirmação de furto de energia ou fraude no medidor**. Dano reputacional alto, e a fila é um perfilamento automatizado.
  3. **Faturas** (inadimplência, atraso, religação após corte): comportamento financeiro e de crédito.
- **O `id_uc` não anonimiza.** É um dado **pseudonimizado** (art. 13, §4º): quem tem o cadastro reidentifica a pessoa. Toda tabela com `id_uc` continua sendo dado pessoal.
- **CNPJ de pessoa jurídica não é dado pessoal**, mas o CNPJ de empresário individual ou MEI, junto com o nome, identifica uma pessoa física.

---

## 2. Mapa por tabela e coluna

**Legenda de risco:** 🔴 alto · 🟠 médio · 🟡 baixo · ⚪ não é dado pessoal sozinho (mas vira, ligado ao `id_uc`)

### Unidades consumidoras (cadastro): a tabela mais crítica

| Coluna | Tipo de dado | Risco | Observação |
|---|---|---|---|
| `cpf_cnpj` | Identificador direto | 🔴 | Vem **sem máscara** no Raw, na Bronze e na Silver. Mascarado só na Gold (`cpf_cnpj_mascarado`). |
| `nome_titular` | Identificador direto | 🔴 | Presente da Raw até a Gold (`dim_unidade_consumidora`, `fila_inspecao`). |
| `logradouro`, `numero`, `cep` | Endereço (identificador) | 🔴 | Junto com o nome, localiza a pessoa. |
| `bairro`, `municipio` | Quase-identificador | 🟡 | Sozinhos, não identificam. |
| `latitude`, `longitude` | Geolocalização | 🟡 | Só 2 casas decimais (~1 km). Baixo risco sozinhas; somadas ao endereço, não acrescentam muito. |
| `classe`, `subgrupo_tarifario`, `data_ligacao`, `status` | Atributos do contrato | 🟡 | Ligados ao titular, compõem o perfil. |
| `id_uc` | Pseudônimo | ⚪ | Chave que liga todas as tabelas à pessoa. |

### Leituras (consumo mensal)

| Coluna | Risco | Observação |
|---|---|---|
| `consumo_kwh`, `leitura_*`, `data_leitura`, `tipo_leitura` | 🟠 | Consumo por residência revela **hábitos e ocupação**: casa vazia, número de moradores, aparelhos. Com a campanha de smart meters, a granularidade tende a aumentar no futuro. |
| `id_medidor` | ⚪ | Identificador de equipamento. |

### Faturas

| Coluna | Risco | Observação |
|---|---|---|
| `status`, `data_pagamento`, `dias_atraso`, `status_pagamento` | 🔴 | **Inadimplência e atraso** são informação de crédito. Vazados com o nome, causam dano reputacional e financeiro. |
| `valor_energia`, `tributos`, `valor_total` | 🟠 | Gasto mensal, um indicador indireto de renda. |
| `bandeira_tarifaria`, `mes_referencia` | ⚪ | Não são pessoais. |

### Inspeções e fila de perdas: maior dano por associação

| Coluna | Risco | Observação |
|---|---|---|
| `resultado` (`IRREGULARIDADE_CONFIRMADA`) | 🔴 | Associa a pessoa a uma possível infração (furto de energia). |
| `tipo_irregularidade` (`LIGACAO_CLANDESTINA`, `MEDIDOR_ADULTERADO`, `BY_PASS`…) | 🔴 | Descreve a conduta suspeita. |
| `kwh_recuperado` | 🟠 | Dá a dimensão da infração. |
| `inspetor` (`INSP-002`) | 🟡 | Dado de **empregado** (código, sem nome). Pseudonimizado. |
| **`fila_inspecao`**: `score`, `motivo_suspeita`, `kwh_recuperavel_estimado_ano` **+ nome + endereço** | 🔴 | **Perfilamento automatizado** que rotula pessoas como suspeitas (art. 20: o titular pode pedir revisão de decisões automatizadas). Num vazamento, é uma "lista de suspeitos" com nome e endereço. |

### Atendimentos

| Coluna | Risco | Observação |
|---|---|---|
| `assunto`, `subassunto` | 🟠 | Alguns revelam situação financeira (`RELIGACAO / APOS PAGAMENTO` = houve corte por falta de pagamento) ou disputa (`DANO ELETRICO / RESSARCIMENTO`, `FATURA / CONTESTACAO`). |
| `nota_satisfacao`, `canal`, datas, `historico` | 🟡 | Comportamento de contato. **Não há campo de texto livre**, o que é bom, porque costuma ser onde aparece o dado mais sensível. |

### Geração distribuída

| Coluna | Risco | Observação |
|---|---|---|
| `potencia_kwp`, `modalidade`, `data_conexao`, `energia_injetada` | 🟡 | Indica patrimônio (painel solar) e um perfil de renda. |

### Medidores e ocorrências de rede

| Tabela | Risco | Observação |
|---|---|---|
| Medidores | 🟡 | Equipamento ligado à UC. |
| Ocorrências | 🟡 | Interrupções por UC; pouco impacto. |

### Registros TESTE

Os 200 `TESTE…` (CPF `00000000000`) são fictícios e não são dados pessoais. Ficam na quarentena das UCs.

---

## 3. Onde os dados pessoais estão hoje

| Camada / destino | CPF | Nome e endereço | Inspeções / fila | Situação |
|---|---|---|---|---|
| **Raw** (Volume `raw_data`) | Aberto | Sim | Sim | Arquivo original; acesso restrito ao workspace |
| **Bronze** | Aberto | Sim | Sim | Cópia fiel da fonte (exigência do case) |
| **Silver** | Aberto (só dígitos) | Sim | Sim | **Inclui as tabelas de quarentena**, que guardam o dado pessoal dos registros rejeitados |
| **Gold** | **Mascarado** (`****…1234`) | Sim | Sim (`fila_inspecao` tem nome e endereço) | Exportada em CSV para o banco local |
| CSV de exportação e banco local | Mascarado | Sim | Sim | ⚠️ Arquivos fora do Databricks: maior risco de vazamento |
| Portal web | Depende das telas | Sim (visão 360) | Sim (fila de perdas) | Precisa de controle por perfil |
| **Agente de IA** | Depende das tabelas expostas | Depende | Depende | ⚠️ O resultado das consultas vai para um **provedor de LLM externo** (Gemini/OpenRouter) |
| **Repositório GitHub público** | — | — | — | ⚠️ **Nenhum dado pode ir para o repositório** |

---

## 4. Riscos principais em caso de vazamento

| # | Cenário | Dano ao titular | Probabilidade no projeto |
|---|---|---|---|
| 1 | **CSV ou banco local (SQLite/Postgres) commitado no GitHub público** | Exposição de toda a base (nome, endereço, inadimplência, suspeitas) | **Alta** se não houver `.gitignore`. O case exige repositório público. |
| 2 | Agente de IA envia nome, endereço ou CPF ao provedor do LLM | Transferência internacional sem controle (art. 33); dado fora do ambiente | Média: depende das tabelas que o agente enxerga |
| 3 | Vazamento da `fila_inspecao` | Pessoas rotuladas como suspeitas de furto, com endereço | Média |
| 4 | Saídas de notebook com amostras (`display`) compartilhadas em prints ou na apresentação | Exposição pontual de nomes e CPFs | Média: prints são exigidos no README e na apresentação |
| 5 | Credenciais (token do Databricks, chave do LLM, senha do banco) no repositório | Acesso a toda a base | Média |
| 6 | Tabelas de quarentena esquecidas, sem o mesmo controle | Dado pessoal de registros rejeitados | Baixa |

---

## 5. Medidas já implementadas no pipeline

| Medida | Onde | Princípio LGPD |
|---|---|---|
| CPF/CNPJ mascarado na Gold (só os 4 últimos dígitos) | `dim_unidade_consumidora` | Necessidade / minimização (art. 6º, III) |
| Registros de teste separados na quarentena | Silver de UCs | Qualidade dos dados (art. 6º, V) |
| Fila de perdas com **`motivo_suspeita` explícito** | `fila_inspecao` | Transparência e revisão de decisão automatizada (art. 20) |
| Rótulos de ação não confiáveis fora da Gold | `silver_atendimento_tratativas` | Qualidade dos dados |
| Coordenadas com baixa precisão (~1 km), herdadas da fonte | Cadastro | Minimização |

---

## 6. Recomendações, por prioridade

### Antes da entrega (obrigatório na prática)

1. **`.gitignore` para todos os dados:** `*.csv`, `*.db`, `*.sqlite`, `*.parquet`, `*.xlsx`, pastas de export e `.env`. No repositório, só código e, se necessário, uma **amostra sintética** gerada para os testes.
2. **Nenhuma credencial no código:** token do Databricks, chave do LLM e senha do banco ficam em variáveis de ambiente e num `.env.example` sem valores.
3. **Prints sem dado pessoal:** no README e nos slides, usar telas com UCs mascaradas ou registros de exemplo. Evitar `display` de nome ou CPF nos notebooks que vão para os prints do Workflow.

### Agente de IA

4. **Expor ao agente só views sem identificadores diretos** (ex.: `vw_ia_*` sem nome, CPF, logradouro e número; com `id_uc`, bairro, município e classe). As perguntas de negócio do case (bairro, classe, município, GD) funcionam sem dado pessoal.
5. Usuário do banco **somente leitura** para o agente (o case já exige que a IA não altere dados).
6. Registrar (log) as consultas geradas: atende a auditoria do case e permite rastrear um acesso indevido.

### Portal

7. **Controle por perfil** (diferencial do case, mas aqui também é proteção): o atendente vê a visão 360 da UC pesquisada; só a equipe de perdas vê a `fila_inspecao`; a diretoria vê agregados.
8. A **fila de perdas é apoio à decisão, não decisão automática**: a ordem de inspeção é gerada por uma pessoa (o gerente), o que já está no fluxo do case. Manter o `motivo_suspeita` visível.

### Plataforma de dados

9. **Separar o cadastro identificado** numa tabela própria (ex.: `dim_titular`: `id_uc`, nome, CPF, endereço), com acesso restrito, e deixar as demais dimensões e fatos só com `id_uc`. Assim, a maioria das análises roda sobre dado pseudonimizado.
10. No Databricks (Unity Catalog), usar **permissões por schema** e, se necessário, máscaras de coluna para o CPF na Silver.
11. Aplicar à quarentena o mesmo controle de acesso da Silver.

### Governança (para citar na apresentação)

12. **Bases legais prováveis:** execução de contrato (art. 7º, V) para faturamento e atendimento; cumprimento de obrigação regulatória (art. 7º, II) para DEC/FEC e o que a ANEEL exige; **legítimo interesse** (art. 7º, IX) para a análise de perdas e a fila, com avaliação de impacto; proteção do crédito (art. 7º, X) para a inadimplência.
13. **Retenção:** definir por quanto tempo Raw, Bronze e quarentena guardam dados identificados.
14. **Incidente:** em caso de vazamento com risco relevante, comunicar a ANPD e os titulares (art. 48). Vale ter um responsável definido no time.

---

## 7. Resumo para a apresentação

> *"Mapeamos os dados pessoais de ponta a ponta. Não há dados sensíveis pela LGPD, mas o cadastro, a inadimplência e o histórico de fiscalização são de alto impacto. O CPF chega mascarado à Gold, o agente de IA só enxerga dados sem identificação direta, a fila de perdas mostra o motivo de cada suspeita e a decisão final é humana, e nenhum dado vai para o repositório público."*

(Os itens 4, 7 e 9 ainda precisam ser implementados para que essa frase seja verdadeira.)
