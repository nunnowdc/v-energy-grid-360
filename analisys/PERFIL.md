# PERFILAMENTO DE DADOS - V-Energy

## 1. Qualidade dos Dados
### Unidades Consumidoras
- **Duplicatas**: 900 linhas duplicadas.
- **Nulos**: CEP (34.6% nulo).
- **Anomalias**: Latitude/Longitude com baixíssima variação (apenas 73 e 38 valores distintos para 46k linhas).

### Medidores
- **Duplicatas**: 513 duplicatas.
- **Nulos**: `data_ultima_manutencao` (100% nulo).
- **Integridade**: 100% dos medidores pertencem a UCs válidas.

### Leituras
- **Anomalias**: Consumo negativo (-14,918 kWh) e valores extremos (60k kWh/mês).
- **Nulos**: `leitura_anterior` (36.5% nulos).

### Faturas
- **Integridade**: Crítica. 41.3% de orfandade em relação às UCs.
- **Formato**: CSV usa separador `;`.

## 2. Chaves e Integridade
- **Chaves Primárias**: `id_uc` (UCs), `id_medidor` (Medidores), `id_leitura` (Leituras), `id_fatura` (Faturas).
- **Integridade Referencial**:
    - UCs $ightarrow$ Faturas: **41.3% Órfãos** (Crítico).
    - Medidores $ightarrow$ Leituras: **14.3% Órfãos** (Moderado).
    - Demais relações: 100% íntegras.

## 3. Proposta de Camada Silver (Limpezas e Regras)
### Cadastro (UCs e Medidores)
- Remover duplicatas de `id_uc`.
- Padronizar endereços e preencher CEPs nulos via geocodificação se possível.
- Tratar a coluna de manutenção de medidores (remover se inútil).

### Leituras
- Tratar consumos negativos (marcar como erro ou estorno).
- Validar `leitura_atual` $\ge$ `leitura_anterior`.
- Limitar outliers de consumo baseados na classe da UC.

### Faturas
- Investigar a perda de 41% dos cadastros de UC ou realizar merge com fontes externas.
- Converter `valor_total` e `tributos` para tipos numéricos (tratar vírgulas/pontos).

### Rede e Operação
- Padronizar categorias de ocorrências e atendimentos.
- Converter datas para formato ISO.

## 4. Dúvidas
- Por que 41% das faturas não possuem UC correspondente no cadastro?
- Qual a regra de negócio para consumos negativos em leituras?
- A base de UCs está incompleta ou a de Faturas contém dados de outras áreas?
