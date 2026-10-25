# V-Energy Grid 360 · Glossário de Domínio

Vocabulário canônico do ecossistema de dados, engenharia e inteligência analítica da V-Energy Grid 360.

## Medição e Consumo

**Leitura**:
Registro do mostrador do medidor em uma data determinada para fins de apuração de consumo.
_Evitar_: Marcação, medição avulsa.

**Consumo Medido**:
Volume de energia apurado entre duas leituras consecutivas (em kWh).
_Evitar_: Consumo bruto, gasto.

## Inspeções e Perdas

**Inspeção Técnica**:
Ação de fiscalização em campo na unidade consumidora para detecção e cessação de fraudes, desvios e anomalias na medição.
_Evitar_: Vistoria, blitz, auditoria de campo.

**kWh Recuperado**:
Volume estimado de energia consumida irregularmente e incorporada para cobrança retroativa após cessação de fraude.
_Evitar_: Energia fraudada, furto recuperado.

**Resultado da Inspeção**:
Classificação canônica da vistoria em `IRREGULARIDADE_CONFIRMADA` ou `SEM_IRREGULARIDADE`.
_Evitar_: Parecer, status da inspeção.

**Irregularidade Confirmada**:
Inspeção com comprovação inequívoca de intervenção indevida ou desvio de energia (ex.: by-pass, medidor adulterado, lacre violado).
_Evitar_: Fraude constatada, gato.

**Sem Irregularidade**:
Inspeção concluída com instalações regulares ou termo de nada consta.
_Evitar_: Normal, regularidade, nada consta.

**Fila de Inspeção**:
Lista analítica priorizada de unidades consumidoras suspeitas de irregularidade de medição direcionada para equipes de campo.
_Evitar_: Fila de corte, lista de fiscalização.

**Score de Suspeita**:
Pontuação heurística normalizada de 0 a 100 indicativa da propensão de fraude ou anomalia de medição em uma unidade consumidora.
_Evitar_: Nota de risco, pontuação de fraude.

**kWh Recuperável Estimado**:
Projeção anualizada do volume de energia não medida que pode ser restabelecido ao faturamento após normalização da medição.
_Evitar_: Furto potencial, ganho estimado.

## Geração Distribuída

**Geração Distribuída (GD)**:
Centrais geradoras de energia elétrica a partir de fontes renováveis conectadas diretamente na rede de distribuição junto a unidades consumidoras.
_Evitar_: Usina solar, microgerador.

**Potência Instalada (kWp)**:
Capacidade nominal de pico do sistema de geração solar fotovoltaica expressa em quilowatt-pico.
_Evitar_: Potência em Watts, capacidade do painel.

**Energia Injetada**:
Volume mensal de excedente de energia elétrica injetada na rede da concessionária após suprir o autoconsumo instantâneo da unidade consumidora.
_Evitar_: Geração total, crédito gerado.

**Energia Estimada**:
Volume de injeção preenchido por estimativa paramétrica padrão (110 kWh/kWp) atribuído a conexões recentes sem histórico prévio de faturamento.
_Evitar_: Injeção fabricada, média padrão.

## Arquitetura de Dados

**Visão 360**:
Consolidação holística de cadastro, medição ativa, geração distribuída e histórico operacional em uma única dimensão por unidade consumidora.
_Evitar_: Tabela única, consolidador.

**Alimentador**:
Circuito elétrico de média tensão responsável por distribuir energia de uma subestação a um conjunto delimitado de unidades consumidoras.
_Evitar_: Circuito de rua, ramal de distribuição.

**Quarentena**:
Armazenamento segregado de registros que violam critérios de integridade referencial ou física para fins de auditoria sem interrupção do pipeline.
_Evitar_: Tabela de erros, descarte, log de rejeição.
