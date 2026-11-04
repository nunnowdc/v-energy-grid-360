# Perfil de dados: `atendimentos.json`

**Status:** quase completo (faltam os itens da seção 7)
**Última atualização:** 24/10/2026
**Fonte:** `/Volumes/v-energy/raw_data/raw_data/atendimentos.json` (JSON multiline, aninhado)

---

## 1. Visão geral

| Item | Valor |
|---|---|
| Registros | **318.871** (o case fala em ~319 mil) |
| Colunas (9) | protocolo, id_uc, assunto, subassunto, canal, data_abertura, data_fechamento, nota_satisfacao, historico |
| `historico` | array de `{acao, canal, data, sequencia}`, nunca nulo nem vazio |
| Tratativas (ações no histórico) | 636.857, cerca de 2 por chamado |
| Período | jul/2022 a jun/2026 (48 meses) |
| UCs com pelo menos 1 chamado | 44.940 das 45.000 (média de ~7 chamados por UC em 4 anos) |

---

## 2. O que veio limpo

Esta é a tabela **mais limpa** do conjunto:

- **Sem duplicatas:** nenhum protocolo repetido.
- **Sem nulos**, exceto `nota_satisfacao`.
- **Formatos únicos:** datas sempre `yyyy-MM-dd HH:mm:ss`, `protocolo` sempre `AT999999999`, `id_uc` sempre `UC999999`.
- **Categorias sem variação de escrita:**
  - `assunto`: 6 valores. FALTA DE ENERGIA 101.306 · FATURA 43.624 · DANO ELETRICO 43.582 · LIGACAO NOVA 43.520 · GERACAO DISTRIBUIDA 43.499 · RELIGACAO 43.340.
  - `canal`: 5 valores. WHATSAPP, TELEFONE, APP, SITE e PRESENCIAL, com ~64 mil cada.
  - `subassunto`: 15 valores, sempre coerentes com o assunto (ver 2.1).
- **Nota de satisfação:** sempre numérica, entre 1,3 e 5,0.

### 2.1 Assunto × subassunto (coerente)

| Assunto | Subassuntos |
|---|---|
| FALTA DE ENERGIA | INTERRUPCAO PARCIAL, INTERRUPCAO TOTAL, OSCILACAO |
| FATURA | CONTESTACAO, SEGUNDA VIA, VALOR ALTO, PARCELAMENTO |
| DANO ELETRICO | VISTORIA, RESSARCIMENTO |
| GERACAO DISTRIBUIDA | VISTORIA, HOMOLOGACAO, CREDITOS |
| LIGACAO NOVA | SOLICITACAO, VISTORIA, PRAZO |
| RELIGACAO | URGENCIA, APOS PAGAMENTO |

`VISTORIA` aparece em 3 assuntos, o que é legítimo.

---

## 3. Problemas encontrados

| # | Problema | Evidência | Tamanho |
|---|---|---|---|
| 1 | Chamados sem nota de satisfação | `nota_satisfacao` nula | 9.566 (3%) |
| 2 | **Histórico com os rótulos de ação aleatórios** | Ver a seção 4 | 81% dos chamados |
| 3 | **Histórico como array**, o que quebra a exportação CSV | Spark não grava array em CSV | Todos os registros |
| 4 | ~~Pico em julho de 2025~~ **não é problema** | Em jul/2025 há cerca de 3 vezes o volume normal em todos os assuntos. A investigação mostrou que é um **evento operacional legítimo**, não um artefato. | Ver a seção 6 |

---

## 4. Resolução da pendência do histórico

Resultado dos testes (ver `pendencia_historico_atendimentos.md`):

| Teste | Resultado | Conclusão |
|---|---|---|
| 1. As ações caem dentro do próprio chamado? | **100%** dentro da janela abertura–fechamento, **100%** no mesmo canal. A última ação sempre coincide com o fechamento (50,07% das ações = 1 por chamado). | O histórico **pertence ao próprio chamado**. Não há mistura entre clientes. |
| 2. A ABERTURA fora de lugar é de outro chamado da mesma UC? | Resultado do cruzamento pendente | (a H1 já está muito enfraquecida pelos testes 1 e 3) |
| 3. A desordem se concentra em algum recorte? | **~81% desordenados em TODOS os recortes**: município de 80,5% a 81,6%, canal de 80,7% a 81,4% | **Ruído aleatório (H3).** |

**Por que 81% indica sorteio:** existem 5 ações possíveis. Se o rótulo da primeira ação fosse sorteado, ele seria ABERTURA em 1/5 dos casos, e ~80% dos chamados "não começariam com abertura". O valor observado (81%) é exatamente o que um sorteio produziria.

**Decisão de tratamento:**
- `data_abertura` e `data_fechamento` são a fonte da verdade para tempo e status do chamado.
- Do histórico, usar **apenas `qtd_tratativas`**.
- **Não usar `teve_despacho`** (proposto antes): se os rótulos são aleatórios, a presença de DESPACHO também é.
- O histórico explodido vai para a `silver_atendimento_tratativas` só por rastreabilidade, documentado no dicionário como "rótulos de ação não confiáveis".

---

## 5. Achados sobre o conteúdo (importantes para o portal e a IA)

| Achado | Evidência | Implicação |
|---|---|---|
| **A nota de satisfação não varia entre canais e assuntos** | Média de **4,04** em todos os 5 canais e em todos os 6 assuntos (4,04–4,05). | A nota **não separa** canais nem assuntos. Não dá para gerar insight do tipo "o canal X atende pior". **Mas ela varia no tempo:** cai para 3,11 em jul/2025 (seção 6). |
| **O tempo de resolução não varia entre assuntos** | Mediana de **124–125 h** (~5,2 dias) em todos os assuntos | Sem sinal para comparar assuntos. **Mas também varia no tempo:** sobe para 363 h em jul/2025 (seção 6). |
| **Volume de chamados estável** | ~5,4 mil por mês em todo o período (exceto jul/2025). FATURA ~850–940 por mês, sem tendência. | Não há aumento de reclamações de fatura acompanhando o reajuste. Os chamados não ajudam a explicar o efeito-preço. |
| **FALTA DE ENERGIA é ~32% dos chamados** | 101.306 de 318.871 | É o principal motivo de contato. O cruzamento com as ocorrências (célula 11) está pendente. |

---

## 6. Pico de julho de 2025: ✅ investigado, é um evento operacional e não um artefato

> **Conclusão (24/10/2026):** a hipótese de artefato foi **descartada**. Os chamados de jul/2025 são registros legítimos, com um comportamento próprio: **volume 3×, satisfação 1 ponto menor e resolução 3× mais lenta**. É o retrato de uma **crise de atendimento**. Os registros **ficam na Silver** e o mês vira um **achado de negócio** (N-06).

### Volume por assunto

| Assunto | Mês típico | jul/2025 | Razão |
|---|---|---|---|

| Assunto | Mês típico | jul/2025 | Razão |
|---|---|---|---|
| FALTA DE ENERGIA | ~2.000 | 6.186 | 3,1× |
| FATURA | ~870 | 2.384 | 2,7× |
| DANO ELETRICO | ~870 | 2.361 | 2,7× |
| GERACAO DISTRIBUIDA | ~870 | 2.339 | 2,7× |
| LIGACAO NOVA | ~870 | 2.406 | 2,8× |
| RELIGACAO | ~870 | 2.385 | 2,7× |

### Hipóteses de artefato testadas (célula 12)

| Hipótese de artefato | Teste | Resultado | Veredito |
|---|---|---|---|
| Lote com uma data padrão | 12a: chamados por dia | **Todos os 31 dias de julho** ficam entre 535 e 629 chamados (~3× os ~210 por dia de junho e agosto). Nenhum dia concentra o excesso. | ❌ Descartada |
| Carga extra adicionada depois | 12b: faixa de protocolos por mês | A numeração é **sequencial e cronológica**: julho ocupa 230.048–248.108, colado em junho (…230.047) e em agosto (248.109…). Não há um bloco no fim da numeração. | ❌ Descartada |
| Cópias de outros meses com data e protocolo novos | 12c: "gêmeos" (mesma UC, assunto, subassunto, canal, hora e duração) | **Nenhum gêmeo encontrado.** | ❌ Descartada |

### O comportamento do mês é diferente (12d)

| Métrica | jul/2025 | Demais meses | Leitura |
|---|---|---|---|
| Chamados | 18.061 | ~6.400 por mês | 2,8× o volume |
| **Nota média** | **3,11** | 4,10 | Queda de ~1 ponto, o único mês com satisfação baixa |
| **Mediana de resolução** | **363 h** (~15 dias) | 120 h (~5 dias) | 3× mais lento |
| % sem nota | 3,1% | 3,0% | Igual |
| Tratativas por chamado | 2 | 2 | Igual |
| UCs distintas | 14.828 | — | O excesso vem de muitas UCs, não de poucos clientes repetindo |

**Por que isso descarta o artefato:** uma duplicação ou um erro de carga copiaria também a nota e o tempo de resolução dos registros originais. Aqui, o mês tem uma **assinatura própria e coerente**: mais demanda gera fila, a fila gera atraso, e o atraso gera insatisfação.

**Por que todos os assuntos sobem juntos:** um evento de rede (tempestade) aumentaria só FALTA DE ENERGIA e DANO ELETRICO. O aumento proporcional em todos os assuntos indica algo que afetou **o atendimento como um todo**: por exemplo, uma troca de sistema de atendimento, um problema generalizado de comunicação com o cliente ou um evento que gerou contatos de todo tipo.

> **✅ Causa identificada (25/10/2026):** um **evento climático** na rede. Em jul/2025 as ocorrências de rede foram 5,3× o normal (17.844), as horas × UC interrompidas 15,7× (87.385), e **97,2% tiveram causa climática** (contra ~16% nos outros meses). As faturas do mês estão normais. Detalhes em `perfil_ocorrencias_rede.md` §7.

**Cruzamentos feitos:**
- `faturas` de jun–jul/2025: houve alguma anomalia de faturamento (atraso, refaturamento, bandeira) que gerou contatos?
- `ocorrencias_rede` de jul/2025: as interrupções também subiram?
- Para o portal e a IA, isso vira um **insight pronto**: "em julho de 2025 o volume de chamados triplicou, o tempo de resolução subiu de 5 para 15 dias e a satisfação caiu de 4,1 para 3,1".

### Tratamento

- **Manter** os registros na Silver. Não são erro.
- Documentar o mês no dicionário de dados como um período atípico.
- Ao calcular médias históricas (satisfação, tempo de resolução), mostrar com e sem jul/2025, ou destacar o mês.

---

## 7. Pendências

- [ ] Célula 9, teste 2: o resultado do cruzamento (`acoes_abertura` × `batem_com_outro_chamado`).
- [ ] Célula 9: a tabela do teste 3 por **assunto**.
- [ ] Célula 10: integridade com o cadastro (órfãos, TESTE).
- [ ] Célula 11: % de chamados de FALTA DE ENERGIA com ocorrência correspondente.
- [x] Célula 12: pico de jul/2025 investigado. É um evento operacional, não um artefato (seção 6).
- [ ] Cruzar jul/2025 com faturas e ocorrências quando esses perfis estiverem prontos.
- [ ] Célula 12: investigação do pico de jul/2025.

---

## 8. O que o notebook atual (`bronze_to_silver.py`) já cobre

| Item | Situação |
|---|---|
| Conversão da nota e das datas | ✅ Funciona, porque os formatos são únicos (mas usa cast comum, não `try_`) |
| Deduplicação | ⚪ Não faz, mas também não há duplicatas |
| Histórico | ❌ Mantém o array, o que quebra o CSV (S-ATE-01) |
| Integridade com o cadastro | ❌ Não verifica |
| Pico de jul/2025 | ⚪ Não detecta, mas também não precisa tratar: é um evento legítimo. Basta documentar. |
