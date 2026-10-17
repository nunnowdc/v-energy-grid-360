# SÍNTESE DA ANÁLISE EXPLORATÓRIA (EDA) - V-Energy Grid 360

## 1. Panorama de Dados
As bases de dados apresentam a seguinte composição volumétrica:
- **Cadastro**: 46k UCs e 51k Medidores.
- **Operacional**: ~2.18M de Faturas e ~2.18M de Leituras.
- **Apoio**: Ocorrências de Rede, Atendimentos e Inspeções.

## 2. Diagnóstico de Qualidade e Integridade (Fatos Observados)

### A. Integridade Referencial (Crítico)
- **Faturas $\rightarrow$ UCs**: 41.3% das faturas referenciam `id_uc` inexistentes no cadastro de unidades consumidoras.
- **Leituras $\rightarrow$ Medidores**: 14.3% das leituras referenciam medidores inexistentes.

### B. Qualidade de Atributos
- **Nulos Sistêmicos**: 
    - Coluna `data_ultima_manutencao` em Medidores é 100% nula.
    - CEPs em UCs apresentam 34.6% de nulos.
- **Inconsistências de Formato**: 
    - Datas em leituras apresentam formatos mistos (ISO e DD/MM/YYYY).
    - Categorias de `classe` em UCs não estão padronizadas (ex: RESIDENCIAL, residencial, Residencial).

### C. Anomalias de Consumo
- **Consumos Negativos**: 8.150 registros detectados, concentrados majoritariamente em leituras do tipo **REAL** (96% dos casos).
- **Outliers**: Presença de consumos extremos (ex: 376k kWh/mês) que fogem completamente ao perfil residencial/comercial comum.

## 3. Plano de Limpeza Sugerido (Camada Silver)

### Cadastro
- Remover duplicatas de `id_uc` e `id_medidor`.
- Padronizar `classe` e `municipio` (Uppercase/Trim).
- Tratar CEPs nulos.

### Operacional (Leituras e Faturas)
- **Tratamento de Órfãos**: Investigar a origem das faturas órfãs antes de descartá-las.
- **Saneamento de Consumo**:
    - Converter consumos negativos em `NaN` ou marcar como 'estorno/erro'.
    - Aplicar filtros de outliers baseados na `classe` da UC.
- **Padronização Temporal**: Converter todas as datas para formato ISO (YYYY-MM-DD).

---
*Data da Síntese: 2026-10-16*
