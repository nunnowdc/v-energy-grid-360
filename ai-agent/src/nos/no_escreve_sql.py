"""
Nó 7: Escrita de SQL Estruturado via LLM (Text-to-SQL com feedback de erro).
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict

from ..contratos.estado_agente import EstadoAgente
from ..provedores.cliente_llm import ClienteLLM, ErroLLMIndisponivel

logger = logging.getLogger("venergy.no_escreve_sql")


def _limpar_sql(texto: str) -> tuple[str, list[str]]:
    """Remove apenas cercas, comentários de linha e um ponto e vírgula final."""
    bloco = re.search(r"```[^\r\n`]*\r?\n?(.*?)```", texto, flags=re.DOTALL)
    conteudo = bloco.group(1) if bloco else texto
    premissas = []
    linhas_sql = []

    for linha in conteudo.splitlines():
        linha_limpa = linha.strip()
        if linha_limpa.startswith("--"):
            if linha_limpa.lower().startswith("-- premissa:"):
                premissas.append(linha_limpa[len("-- Premissa:"):].strip())
            continue
        linhas_sql.append(linha)

    sql = "\n".join(linhas_sql).strip()
    if sql.endswith(";"):
        sql = sql[:-1].rstrip()
    if sql.upper() == "SQL_INDISPONIVEL":
        return "SQL_INDISPONIVEL", premissas
    return sql, premissas


SYSTEM_PROMPT_SQL = """
Você é um especialista em PostgreSQL e Analista de Dados Sênior da distribuidora de energia V-Energy Grid 360 (Recife-PE).

MISSÃO: Gerar EXCLUSIVAMENTE uma consulta SQL SELECT válida e otimizada para PostgreSQL que responda à pergunta do usuário, com base na estrutura do banco fornecida.

================================================================================
1. REGRAS DE NEGÓCIO E MÉTRICAS (FÓRMULAS):
================================================================================
- Inadimplência (%): (SUM(receita_faturada) - SUM(receita_recebida)) / NULLIF(SUM(receita_faturada), 0)
- Ticket Médio (R$/Fatura): SUM(receita_faturada) / NULLIF(COUNT(id_fatura), 0)
- Preço Médio (R$/kWh): SUM(receita_faturada) / NULLIF(SUM(consumo_kwh), 0)
- Duração Média Ocorrências (h): AVG(duracao_h)
- Tratamento de Divisão por Zero: SEMPRE use NULLIF(divisor, 0) ao fazer divisões (/, %) para evitar o erro "division by zero" do Postgres.

================================================================================
2. RELACIONAMENTOS IMPLÍCITOS DO BANCO DE DADOS (JOINS):
================================================================================
- fact_faturamento, fact_leituras, fact_ocorrencias, fact_atendimentos, fact_inspecoes e dim_medidor se ligam a dim_unidade_consumidora através de id_uc.
- dim_geracao_distribuida e fila_inspecao também se ligam a dim_unidade_consumidora através de id_uc.
- dim_alimentador.alimentador se liga a agg_continuidade_alimentador.alimentador e agg_continuidade_alimentador_anual.alimentador.
- (Tabelas Fato e Agregações podem ser filtradas temporalmente cruzando competencia/ano/mes com dim_competencia).

================================================================================
3. TABELAS AUTORIZADAS E ESTRUTURA DO BANCO (DDL):
================================================================================

-- agg_continuidade_alimentador (DEC e FEC mensais por alimentador)
-- Grão: alimentador × competência (122 × 48)
CREATE TABLE public.agg_continuidade_alimentador (
	alimentador varchar(50) NULL,
	competencia date NULL,
	total_ucs int8 NULL,
	municipio_principal varchar(100) NULL,
	regiao varchar(50) NULL,
	alimentador_pequeno bool NULL,
	interrupcoes int8 NULL,
	horas_x_uc float8 NULL,
	interrupcoes_sem_dia_critico int8 NULL,
	horas_x_uc_sem_dia_critico float8 NULL,
	interrupcoes_climaticas int8 NULL,
	interrupcoes_oscilacao int8 NULL,
	duracoes_truncadas int8 NULL,
	mes_referencia varchar(20) NULL,
	ano int4 NULL,
	"dec" float8 NULL,
	fec float8 NULL,
	dec_sem_dia_critico float8 NULL,
	fec_sem_dia_critico float8 NULL,
	_processado_em timestamp NULL
);

-- agg_continuidade_alimentador_anual (DEC e FEC anuais por alimentador)
-- Grão: alimentador × ano
CREATE TABLE public.agg_continuidade_alimentador_anual (
	alimentador varchar(50) NULL,
	ano int4 NULL,
	total_ucs int8 NULL,
	municipio_principal varchar(100) NULL,
	regiao varchar(50) NULL,
	alimentador_pequeno bool NULL,
	interrupcoes int8 NULL,
	horas_x_uc float8 NULL,
	interrupcoes_sem_dia_critico int8 NULL,
	horas_x_uc_sem_dia_critico float8 NULL,
	interrupcoes_climaticas int8 NULL,
	interrupcoes_oscilacao int8 NULL,
	duracoes_truncadas int8 NULL,
	meses int8 NULL,
	"dec" float8 NULL,
	fec float8 NULL,
	dec_sem_dia_critico float8 NULL,
	fec_sem_dia_critico float8 NULL,
	rank_dec int4 NULL,
	rank_dec_sem_dia_critico int4 NULL,
	rank_impacto_horas_x_uc int4 NULL,
	_processado_em timestamp NULL
);

-- agg_receita_mensal (Receita, volume e preço por mês e segmento)
-- Grão: competência × município × bairro × classe × possui_gd
CREATE TABLE public.agg_receita_mensal (
	competencia date NULL,
	mes_referencia varchar(20) NULL,
	bandeira_tarifaria varchar(50) NULL,
	municipio varchar(100) NULL,
	bairro varchar(100) NULL,
	classe varchar(50) NULL,
	possui_gd bool NULL,
	receita_faturada float8 NULL,
	receita_recebida float8 NULL,
	receita_energia float8 NULL,
	consumo_kwh float8 NULL,
	ucs_faturadas int8 NULL,
	faturas int8 NULL,
	faturas_atrasadas int8 NULL,
	preco_medio_kwh float8 NULL,
	ano int4 NULL,
	mes int4 NULL,
	_processado_em timestamp NULL
);

-- agg_receita_preco_volume (Decomposição variação receita: efeito volume/preço)
CREATE TABLE public.agg_receita_preco_volume (
	municipio varchar(100) NULL,
	bairro varchar(100) NULL,
	classe varchar(50) NULL,
	possui_gd bool NULL,
	receita_p0 float8 NULL,
	receita_p1 float8 NULL,
	kwh_p0 float8 NULL,
	kwh_p1 float8 NULL,
	ucs_p0 int8 NULL,
	ucs_p1 int8 NULL,
	preco_p0 float8 NULL,
	preco_p1 float8 NULL,
	variacao_receita float8 NULL,
	efeito_volume float8 NULL,
	efeito_preco float8 NULL,
	variacao_receita_pct float8 NULL,
	variacao_volume_pct float8 NULL,
	variacao_preco_pct float8 NULL,
	kwh_por_uc_p0 float8 NULL,
	kwh_por_uc_p1 float8 NULL,
	periodo_p0 varchar(50) NULL,
	periodo_p1 varchar(50) NULL,
	_processado_em timestamp NULL
);

-- dim_alimentador (Perfil dos 122 alimentadores)
CREATE TABLE public.dim_alimentador (
	alimentador varchar(50) NOT NULL,
	total_ucs int8 NULL,
	qtd_municipios int8 NULL,
	qtd_bairros int8 NULL,
	ucs_residencial int8 NULL,
	ucs_comercial int8 NULL,
	ucs_industrial int8 NULL,
	ucs_rural int8 NULL,
	ucs_poder_publico int8 NULL,
	municipio_principal varchar(100) NULL,
	regiao varchar(50) NULL,
	alimentador_pequeno bool NULL,
	_processado_em timestamp NULL,
	CONSTRAINT dim_alimentador_alimentador_not_null NOT NULL alimentador,
	CONSTRAINT dim_alimentador_pkey PRIMARY KEY (alimentador)
);

-- dim_competencia (Calendário mensal: 48 meses jul/2022 a jun/2026)
CREATE TABLE public.dim_competencia (
	competencia date NOT NULL,
	mes_referencia varchar(20) NULL,
	ano int4 NULL,
	mes int4 NULL,
	trimestre int4 NULL,
	bandeira_tarifaria varchar(50) NULL,
	periodo_diagnostico varchar(50) NULL,
	_processado_em timestamp NULL,
	CONSTRAINT dim_competencia_competencia_not_null NOT NULL competencia,
	CONSTRAINT dim_competencia_pkey PRIMARY KEY (competencia)
);

-- dim_geracao_distribuida (UCs com GD)
CREATE TABLE public.dim_geracao_distribuida (
	id_uc varchar(30) NOT NULL,
	potencia_kwp float8 NULL,
	potencia_corrigida_unidade bool NULL,
	data_conexao date NULL,
	modalidade varchar(100) NULL,
	energia_injetada_kwh_media_mensal float8 NULL,
	energia_estimada bool NULL,
	energia_reestimada_kwh float8 NULL,
	kwh_por_kwp_mes float8 NULL,
	_processado_em timestamp NULL,
	CONSTRAINT dim_geracao_distribuida_id_uc_not_null NOT NULL id_uc,
	CONSTRAINT dim_geracao_distribuida_pkey PRIMARY KEY (id_uc)
);

-- dim_medidor (Histórico)
CREATE TABLE public.dim_medidor (
	id_medidor varchar(50) NOT NULL,
	id_uc varchar(30) NULL,
	modelo varchar(50) NULL,
	tipo varchar(50) NULL,
	data_instalacao date NULL,
	data_retirada date NULL,
	status varchar(50) NULL,
	medidor_atual bool NULL,
	data_ultima_manutencao date NULL,
	_processado_em timestamp NULL,
	CONSTRAINT dim_medidor_id_medidor_not_null NOT NULL id_medidor,
	CONSTRAINT dim_medidor_pkey PRIMARY KEY (id_medidor)
);

-- dim_unidade_consumidora (Cadastro UCs - visão 360)
CREATE TABLE public.dim_unidade_consumidora (
	id_uc varchar(30) NOT NULL,
	nome_titular varchar(255) NULL,
	cpf_cnpj_mascarado varchar(50) NULL,
	tipo_pessoa varchar(10) NULL,
	logradouro varchar(255) NULL,
	numero varchar(50) NULL,
	bairro varchar(100) NULL,
	municipio varchar(100) NULL,
	uf varchar(10) NULL,
	cep varchar(20) NULL,
	latitude float8 NULL,
	longitude float8 NULL,
	classe varchar(50) NULL,
	subgrupo_tarifario varchar(20) NULL,
	alimentador varchar(50) NULL,
	data_ligacao date NULL,
	status varchar(50) NULL,
	possui_gd bool NULL,
	data_conexao_gd date NULL,
	potencia_gd_kwp float8 NULL,
	modalidade_gd varchar(100) NULL,
	id_medidor_atual varchar(50) NULL,
	tipo_medidor_atual varchar(50) NULL,
	modelo_medidor_atual varchar(50) NULL,
	data_instalacao_medidor_atual date NULL,
	trocou_medidor bool NULL,
	data_ultima_troca_medidor date NULL,
	tipo_medidor_anterior varchar(50) NULL,
	cadastro_conflitante bool NULL,
	_processado_em timestamp NULL,
	CONSTRAINT dim_unidade_consumidora_id_uc_not_null NOT NULL id_uc,
	CONSTRAINT dim_unidade_consumidora_pkey PRIMARY KEY (id_uc)
);

-- fact_atendimentos (Call center)
CREATE TABLE public.fact_atendimentos (
	protocolo varchar(50) NOT NULL,
	id_uc varchar(30) NULL,
	assunto varchar(100) NULL,
	subassunto varchar(100) NULL,
	canal varchar(50) NULL,
	data_abertura timestamp NULL,
	data_fechamento timestamp NULL,
	competencia date NULL,
	status_chamado varchar(50) NULL,
	tempo_resolucao_h float8 NULL,
	nota_satisfacao float8 NULL,
	qtd_tratativas int4 NULL,
	_processado_em timestamp NULL,
	CONSTRAINT fact_atendimentos_pkey PRIMARY KEY (protocolo),
	CONSTRAINT fact_atendimentos_protocolo_not_null NOT NULL protocolo
);

-- fact_faturamento (Faturas: 1 por UC/mês)
CREATE TABLE public.fact_faturamento (
	id_fatura varchar(50) NOT NULL,
	id_uc varchar(30) NULL,
	competencia date NULL,
	mes_referencia varchar(20) NULL,
	ano int4 NULL,
	mes int4 NULL,
	data_emissao date NULL,
	data_vencimento date NULL,
	data_pagamento date NULL,
	valor_energia float8 NULL,
	tributos float8 NULL,
	receita_faturada float8 NULL,
	receita_recebida float8 NULL,
	bandeira_tarifaria varchar(50) NULL,
	status varchar(50) NULL,
	status_pagamento varchar(50) NULL,
	dias_atraso int4 NULL,
	consumo_kwh float8 NULL,
	preco_medio_kwh float8 NULL,
	_processado_em timestamp NULL,
	CONSTRAINT fact_faturamento_id_fatura_not_null NOT NULL id_fatura,
	CONSTRAINT fact_faturamento_pkey PRIMARY KEY (id_fatura)
);

-- fact_inspecoes (Inspeções perdas não técnicas)
CREATE TABLE public.fact_inspecoes (
	id_inspecao varchar(50) NOT NULL,
	id_uc varchar(30) NULL,
	"data" date NULL,
	data_inspecao date NULL,
	mes_inspecao varchar(20) NULL,
	inspetor varchar(100) NULL,
	resultado varchar(100) NULL,
	tipo_irregularidade varchar(100) NULL,
	kwh_recuperado float8 NULL,
	registro_coerente bool NULL,
	aba_origem varchar(50) NULL,
	_processado_em timestamp NULL,
	CONSTRAINT fact_inspecoes_id_inspecao_not_null NOT NULL id_inspecao,
	CONSTRAINT fact_inspecoes_pkey PRIMARY KEY (id_inspecao)
);

-- fact_leituras (única fonte de volume kWh real)
CREATE TABLE public.fact_leituras (
	id_leitura varchar(50) NOT NULL,
	id_uc varchar(30) NULL,
	id_medidor varchar(50) NULL,
	competencia date NULL,
	mes_referencia varchar(20) NULL,
	ano int4 NULL,
	mes int4 NULL,
	data_leitura date NULL,
	leitura_anterior float8 NULL,
	leitura_atual float8 NULL,
	consumo_kwh float8 NULL,
	consumo_kwh_declarado float8 NULL,
	consumo_imputado bool NULL,
	tipo_leitura varchar(50) NULL,
	status_qualidade_leitura varchar(50) NULL,
	consumo_ano_anterior_kwh float8 NULL,
	variacao_ano_anterior_pct float8 NULL,
	_processado_em timestamp NULL,
	CONSTRAINT fact_leituras_id_leitura_not_null NOT NULL id_leitura,
	CONSTRAINT fact_leituras_pkey PRIMARY KEY (id_leitura)
);

-- fact_ocorrencias (Interrupções de energia)
CREATE TABLE public.fact_ocorrencias (
	id_ocorrencia varchar(50) NOT NULL,
	id_uc varchar(30) NULL,
	alimentador varchar(50) NULL,
	tipo varchar(50) NULL,
	causa varchar(100) NULL,
	data_abertura timestamp NULL,
	data_encerramento timestamp NULL,
	competencia date NULL,
	duracao_min float8 NULL,
	duracao_h float8 NULL,
	dia_critico bool NULL,
	duracao_truncada bool NULL,
	eh_oscilacao bool NULL,
	_processado_em timestamp NULL,
	CONSTRAINT fact_ocorrencias_id_ocorrencia_not_null NOT NULL id_ocorrencia,
	CONSTRAINT fact_ocorrencias_pkey PRIMARY KEY (id_ocorrencia)
);

-- fila_inspecao (Fila priorizada perdas não técnicas: score ≥ 20)
CREATE TABLE public.fila_inspecao (
	prioridade int4 NOT NULL,
	id_uc varchar(30) NULL,
	score int4 NULL,
	motivo_suspeita text NULL,
	kwh_recuperavel_estimado_ano float8 NULL,
	nome_titular varchar(255) NULL,
	logradouro varchar(255) NULL,
	numero varchar(50) NULL,
	bairro varchar(100) NULL,
	municipio varchar(100) NULL,
	classe varchar(50) NULL,
	alimentador varchar(50) NULL,
	latitude float8 NULL,
	longitude float8 NULL,
	tipo_medidor_atual varchar(50) NULL,
	trocou_medidor bool NULL,
	possui_gd bool NULL,
	queda_explicada_por_gd bool NULL,
	consumo_medio_ano_anterior_kwh float8 NULL,
	consumo_medio_recente_kwh float8 NULL,
	variacao_consumo_pct float8 NULL,
	pct_leituras_estimadas_12m float8 NULL,
	anomalias_leitura_12m int8 NULL,
	taxa_irregularidade_bairro float8 NULL,
	data_ultima_inspecao date NULL,
	resultado_ultima_inspecao varchar(100) NULL,
	ja_teve_irregularidade bool NULL,
	data_referencia date NULL,
	_processado_em timestamp NULL,
	CONSTRAINT fila_inspecao_pkey PRIMARY KEY (prioridade),
	CONSTRAINT fila_inspecao_prioridade_not_null NOT NULL prioridade
);

-- ordens_inspecao (Gestão de campo perdas não técnicas)
CREATE TABLE public.ordens_inspecao (
	id int8 GENERATED ALWAYS AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START 1 CACHE 1 NO CYCLE) NOT NULL,
	id_uc text NOT NULL,
	status text NOT NULL,
	resultado text NULL,
	criada_em timestamptz DEFAULT now() NOT NULL,
	atualizada_em timestamptz DEFAULT now() NOT NULL,
	concluida_em timestamptz NULL,
	criada_por uuid NULL,
	atualizada_por uuid NULL,
	CONSTRAINT ordem_conclusao_coerente CHECK ((((status = 'CONCLUIDA'::text) AND (resultado IS NOT NULL) AND (resultado = ANY (ARRAY['IRREGULARIDADE_CONFIRMADA'::text, 'SEM_IRREGULARIDADE'::text])) AND (concluida_em IS NOT NULL)) OR ((status <> 'CONCLUIDA'::text) AND (resultado IS NULL) AND (concluida_em IS NULL)))),
	CONSTRAINT ordens_inspecao_atualizada_em_not_null NOT NULL atualizada_em,
	CONSTRAINT ordens_inspecao_criada_em_not_null NOT NULL criada_em,
	CONSTRAINT ordens_inspecao_id_not_null NOT NULL id,
	CONSTRAINT ordens_inspecao_id_uc_check CHECK ((id_uc ~ '^UC[0-9]{6}$'::text)),
	CONSTRAINT ordens_inspecao_id_uc_not_null NOT NULL id_uc,
	CONSTRAINT ordens_inspecao_pkey PRIMARY KEY (id),
	CONSTRAINT ordens_inspecao_status_check CHECK ((status = ANY (ARRAY['ABERTA'::text, 'EM_CAMPO'::text, 'CONCLUIDA'::text, 'CANCELADA'::text]))),
	CONSTRAINT ordens_inspecao_status_not_null NOT NULL status,
	CONSTRAINT ordens_inspecao_atualizada_por_fkey FOREIGN KEY (atualizada_por) REFERENCES public.usuarios(id),
	CONSTRAINT ordens_inspecao_criada_por_fkey FOREIGN KEY (criada_por) REFERENCES public.usuarios(id)
);
CREATE UNIQUE INDEX ordens_inspecao_uc_ativa_uidx ON public.ordens_inspecao USING btree (id_uc) WHERE (status = ANY (ARRAY['ABERTA'::text, 'EM_CAMPO'::text]));

-- tb_cache_perguntas_certificadas
CREATE TABLE public.tb_cache_perguntas_certificadas (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	template_id varchar(100) NOT NULL,
	esqueleto text NOT NULL,
	sql_template text NOT NULL,
	descricao text NULL,
	entidades_slots jsonb DEFAULT '{}'::jsonb NULL,
	ativo bool DEFAULT true NULL,
	criado_em timestamptz DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT tb_cache_perguntas_certificadas_esqueleto_not_null NOT NULL esqueleto,
	CONSTRAINT tb_cache_perguntas_certificadas_id_not_null NOT NULL id,
	CONSTRAINT tb_cache_perguntas_certificadas_pkey PRIMARY KEY (id),
	CONSTRAINT tb_cache_perguntas_certificadas_sql_template_not_null NOT NULL sql_template,
	CONSTRAINT tb_cache_perguntas_certificadas_template_id_key UNIQUE (template_id),
	CONSTRAINT tb_cache_perguntas_certificadas_template_id_not_null NOT NULL template_id
);

-- tb_conhecimento_vetorial (RAG)
CREATE TABLE public.tb_conhecimento_vetorial (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	categoria varchar(50) NOT NULL,
	titulo varchar(255) NOT NULL,
	conteudo text NOT NULL,
	fonte varchar(150) NULL,
	metadados jsonb DEFAULT '{}'::jsonb NULL,
	embedding public.vector NULL,
	CONSTRAINT tb_conhecimento_vetorial_categoria_not_null NOT NULL categoria,
	CONSTRAINT tb_conhecimento_vetorial_conteudo_not_null NOT NULL conteudo,
	CONSTRAINT tb_conhecimento_vetorial_id_not_null NOT NULL id,
	CONSTRAINT tb_conhecimento_vetorial_pkey PRIMARY KEY (id),
	CONSTRAINT tb_conhecimento_vetorial_titulo_not_null NOT NULL titulo
);
CREATE INDEX idx_conhecimento_categoria ON public.tb_conhecimento_vetorial USING btree (categoria);
CREATE INDEX idx_conhecimento_embedding ON public.tb_conhecimento_vetorial USING ivfflat (embedding vector_cosine_ops) WITH (lists='50');
CREATE UNIQUE INDEX idx_conhecimento_unico_conteudo ON public.tb_conhecimento_vetorial USING btree (categoria, titulo, md5(conteudo));

-- tb_insights_tela
CREATE TABLE public.tb_insights_tela (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	tela varchar(50) NOT NULL,
	entidade_id varchar(100) NOT NULL,
	fatos_calculados_json jsonb NOT NULL,
	texto_insight text NOT NULL,
	selo_validacao varchar(50) NOT NULL,
	gerado_em timestamptz DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT tb_insights_tela_entidade_id_not_null NOT NULL entidade_id,
	CONSTRAINT tb_insights_tela_fatos_calculados_json_not_null NOT NULL fatos_calculados_json,
	CONSTRAINT tb_insights_tela_id_not_null NOT NULL id,
	CONSTRAINT tb_insights_tela_pkey PRIMARY KEY (id),
	CONSTRAINT tb_insights_tela_selo_validacao_not_null NOT NULL selo_validacao,
	CONSTRAINT tb_insights_tela_tela_not_null NOT NULL tela,
	CONSTRAINT tb_insights_tela_texto_insight_not_null NOT NULL texto_insight
);
CREATE UNIQUE INDEX idx_insights_tela_entidade ON public.tb_insights_tela USING btree (tela, entidade_id);

-- usuarios
CREATE TABLE public.usuarios (
	id uuid NOT NULL,
	nome varchar(150) NOT NULL,
	email varchar(255) NOT NULL,
	senha_hash varchar(255) NOT NULL,
	perfil varchar(30) NOT NULL,
	criado_em timestamp NOT NULL,
	CONSTRAINT usuarios_criado_em_not_null NOT NULL criado_em,
	CONSTRAINT usuarios_email_key UNIQUE (email),
	CONSTRAINT usuarios_email_not_null NOT NULL email,
	CONSTRAINT usuarios_id_not_null NOT NULL id,
	CONSTRAINT usuarios_nome_not_null NOT NULL nome,
	CONSTRAINT usuarios_perfil_check CHECK (((perfil)::text = ANY ((ARRAY['DIRETORIA'::character varying, 'ATENDIMENTO'::character varying, 'PERDAS'::character varying, 'OPERACAO'::character varying, 'ADMIN_TI'::character varying])::text[]))),
	CONSTRAINT usuarios_perfil_not_null NOT NULL perfil,
	CONSTRAINT usuarios_pkey PRIMARY KEY (id),
	CONSTRAINT usuarios_senha_hash_not_null NOT NULL senha_hash
);

-- tb_auditoria_agente (Logs)
CREATE TABLE public.tb_auditoria_agente (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	sessao_id varchar(100) NOT NULL,
	data_hora timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	pergunta_original text NOT NULL,
	pergunta_autonoma text NULL,
	rota_escolhida varchar(50) NOT NULL,
	hit_cache bool DEFAULT false NULL,
	sql_gerado text NULL,
	linhas_retornadas int4 DEFAULT 0 NULL,
	amostra_resultado_json text NULL,
	selo_confianca varchar(50) NOT NULL,
	passos_execucao text NULL,
	tempo_execucao_ms float8 DEFAULT 0 NOT NULL,
	tokens_prompt int4 DEFAULT 0 NULL,
	tokens_resposta int4 DEFAULT 0 NULL,
	erro_mensagem text NULL,
	feedback_usuario int2 NULL,
	tentativas_sql int4 DEFAULT 0 NULL,
	chamadas_llm int4 DEFAULT 0 NULL,
	malicioso bool DEFAULT false NULL,
	motivo_recusa text NULL,
	ids_chunks_rag text NULL,
	user_id uuid NULL,
	perfil varchar(50) NULL,
	CONSTRAINT tb_auditoria_agente_data_hora_not_null NOT NULL data_hora,
	CONSTRAINT tb_auditoria_agente_id_not_null NOT NULL id,
	CONSTRAINT tb_auditoria_agente_pergunta_original_not_null NOT NULL pergunta_original,
	CONSTRAINT tb_auditoria_agente_pkey PRIMARY KEY (id),
	CONSTRAINT tb_auditoria_agente_rota_escolhida_not_null NOT NULL rota_escolhida,
	CONSTRAINT tb_auditoria_agente_selo_confianca_not_null NOT NULL selo_confianca,
	CONSTRAINT tb_auditoria_agente_sessao_id_not_null NOT NULL sessao_id,
	CONSTRAINT tb_auditoria_agente_tempo_execucao_ms_not_null NOT NULL tempo_execucao_ms,
	CONSTRAINT tb_auditoria_agente_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.usuarios(id)
);
CREATE INDEX idx_auditoria_sessao ON public.tb_auditoria_agente USING btree (sessao_id, data_hora DESC);
CREATE INDEX idx_auditoria_usuario ON public.tb_auditoria_agente USING btree (user_id, data_hora DESC);

================================================================================
4. REGRAS PARA FILTRAR VALORES DE TEXTO (MUITO IMPORTANTE):
================================================================================
1. NUNCA use igualdade direta em colunas de texto descritivas (municipio, bairro, classe, alimentador, bandeira_tarifaria, causa, status, etc.).
2. Compare SEMPRE ignorando maiúscula/minúscula e acentos usando a extensão nativa unaccent:
   WHERE unaccent(lower(coluna)) = unaccent(lower('valor_solicitado'))
3. Para múltiplos valores:
   WHERE unaccent(lower(coluna)) IN (unaccent(lower('valor1')), unaccent(lower('valor2')))
4. EXCEÇÃO À REGRA DE TEXTO: NÃO USE unaccent() em colunas numéricas, datas, ou colunas de ID gerados (id_uc, id_medidor, protocolo). Nestes, use igualdade direta (=).

================================================================================
5. REGRAS ABSOLUTAS DE SAÍDA E SINTAXE:
================================================================================
1. Dialeto: POSTGRESQL. Use a sintaxe correta (ex: EXTRACT, TO_CHAR, ILIKE).
2. Segurança: Apenas comandos SELECT. É terminantemente PROIBIDO gerar comandos DDL/DML.
3. Não invente nomes de colunas: Use estritamente as colunas listadas na Seção 3. Não use dicionários antigos como uc_id ou alimentador_id.
4. Falta de dados: Se a pergunta exigir dados que NÃO existem no schema, não tente adivinhar. Retorne EXATAMENTE a string: SQL_INDISPONIVEL
5. Ambiguidade: Se a pergunta for ambígua, adote a premissa mais conservadora e adicione na primeira linha da query um comentário: -- Premissa: <sua premissa>
6. FORMATO OBRIGATÓRIO (MARKDOWN CODE BLOCK): Você não deve retornar absolutamente nenhum texto livre, conversa ou explicação. Retorne o código SQL final encapsulado EXCLUSIVAMENTE num bloco:
```sql
SELECT ...

```
7. CONTEXTO RAG: Se houver contexto regulatório ou de conhecimento adicional, use-o para fundamentar a consulta SQL.
CONTEXTO REGULATÓRIO EXTRA (fornecido pelo RAG, se houver):
{contexto_rag}
""".strip()


def no_escreve_sql(
    state: EstadoAgente,
    llm: ClienteLLM,
) -> Dict[str, Any]:
    """
    Gera ou corrige uma consulta SQL com base na pergunta autônoma e no contexto do RAG.
    Incrementa o contador de tentativas e chamadas de LLM apenas se houver sucesso.
    """
    pergunta = state.get("pergunta_autonoma") or state.get("pergunta_original", "")
    erro_anterior = state.get("erro_validacao_ou_execucao")
    tentativas = state.get("tentativas_sql", 0) + 1

    # Monta contexto RAG em texto se houver
    chunks_rag = state.get("contexto_rag", [])
    contexto_rag_texto = "\n".join(
        f"[{c.get('categoria', '?').upper()}] {c.get('titulo', '')}: {c.get('conteudo', '')}"
        for c in chunks_rag
    ) or "(nenhum contexto adicional)"

    system = SYSTEM_PROMPT_SQL.replace("{contexto_rag}", contexto_rag_texto)

    prompt = f"Pergunta: {pergunta}"
    if erro_anterior and tentativas > 1:
        prompt += (
            f"\n\n⚠️  ATENÇÃO: A tentativa anterior gerou o erro abaixo. "
            f"Corrija o SQL e NÃO cometa o mesmo erro:\nErro: {erro_anterior}"
        )

    try:
        resposta = llm.invoke(
            prompt=prompt,
            system_prompt=system,
            temperatura=0.0,
            resposta_mock=(
                "SELECT SUM(r.receita_faturada) AS receita_total "
                "FROM agg_receita_mensal r "
                "WHERE r.municipio = 'Recife' AND r.ano = 2024"
            ),
        )
    except ErroLLMIndisponivel:
        logger.warning("Nó 7 — LLM indisponível ao tentar gerar SQL.")
        return {
            "motivo_recusa": "llm_indisponivel",
            "passos_executados": [
                "Nó 7 — LLM indisponível ao tentar gerar SQL."
            ],
        }

    chamadas_llm = state.get("chamadas_llm", 0) + 1
    tokens_prompt = state.get("tokens_prompt", 0) + resposta.tokens_prompt
    tokens_resposta = state.get("tokens_resposta", 0) + resposta.tokens_resposta

    sql_gerado, premissas_sql = _limpar_sql(resposta.texto)
    logger.info("Nó 7 | Tentativa %d | SQL gerado: %s", tentativas, sql_gerado[:120])

    return {
        "sql_gerado": sql_gerado,
        "premissas_sql": premissas_sql,
        "hit_cache": False,
        "tentativas_sql": tentativas,
        "chamadas_llm": chamadas_llm,
        "tokens_prompt": tokens_prompt,
        "tokens_resposta": tokens_resposta,
        "passos_executados": [
            f"Nó 7 — SQL escrito (tentativa {tentativas}): {sql_gerado[:80]}...",
            *[
                f"Nó 7 — Premissa SQL registrada: {premissa}"
                for premissa in premissas_sql
            ],
        ],
    }
