"""
Testes unitários para cada nó isolado do pipeline LangGraph do V-Energy Grid 360.
Valida contratos de entrada/saída, bypasses de economia de tokens e tratamento de exceções.
"""
from __future__ import annotations

import pytest
from ai_agent.src.interfaces.stub_validador_sql import StubValidadorSQL
from ai_agent.src.services.sql_executor import SQLExecutor
from ai_agent.src.nos.no_completa_followup import no_completa_followup
from ai_agent.src.nos.no_checa_escopo import no_checa_escopo, rota_pos_escopo
from ai_agent.src.nos.no_roteador_consulta import no_roteador_consulta, rota_pos_roteador
from ai_agent.src.nos.no_escreve_sql import no_escreve_sql
from ai_agent.src.nos.no_valida_sql import no_valida_sql, rota_pos_validacao
from ai_agent.src.nos.no_executa_sql import no_executa_sql, rota_pos_execucao
from ai_agent.src.nos.no_recusa_honesta import no_recusa_honesta
from ai_agent.src.nos.no_sintetiza_resposta import no_sintetiza_resposta
from ai_agent.src.nos.no_finaliza_auditoria import no_finaliza_auditoria


# ── Nó 2: Follow-up ──────────────────────────────────────────────────────────
def test_no_completa_followup_sem_historico(fake_llm_factory):
    """Primeira pergunta da conversa deve fazer bypass do LLM para economia de tokens."""
    fake_llm = fake_llm_factory()
    estado = {
        "pergunta_original": "Qual o faturamento de Olinda em 2023?",
        "historico_recente": [],
        "chamadas_llm": 0,
    }
    resultado = no_completa_followup(estado, llm=fake_llm)

    assert resultado["pergunta_autonoma"] == "Qual o faturamento de Olinda em 2023?"
    assert len(fake_llm.historico_chamadas) == 0  # 0 chamadas de LLM (bypass)


def test_no_completa_followup_com_historico(fake_llm_factory):
    """Pergunta elíptica deve ser contextualizada usando o histórico recente."""
    pergunta_reescrita = "Qual foi o faturamento da classe comercial em Olinda no ano de 2023?"
    fake_llm = fake_llm_factory(resposta_padrao=pergunta_reescrita)
    estado = {
        "pergunta_original": "E as comerciais?",
        "historico_recente": [
            {"role": "user", "content": "Qual o faturamento residencial em Olinda em 2023?"},
            {"role": "assistant", "content": "O faturamento residencial foi de R$ 500.000,00."},
        ],
        "chamadas_llm": 0,
    }
    resultado = no_completa_followup(estado, llm=fake_llm)

    assert resultado["pergunta_autonoma"] == pergunta_reescrita
    assert resultado["chamadas_llm"] == 1
    assert len(fake_llm.historico_chamadas) == 1


# ── Nó 3: Checagem de Escopo ─────────────────────────────────────────────────
def test_no_checa_escopo_heuristica_positiva(fake_llm_factory):
    """Termos explícitos do domínio de energia em Recife/Olinda são aprovados sem chamar LLM."""
    fake_llm = fake_llm_factory()
    estado = {"pergunta_autonoma": "Qual o consumo de energia em Boa Viagem no mês passado?"}
    resultado = no_checa_escopo(estado, llm=fake_llm)

    assert resultado["dentro_escopo"] is True
    assert len(fake_llm.historico_chamadas) == 0
    assert rota_pos_escopo(resultado) == "dentro_escopo"


def test_no_checa_escopo_heuristica_negativa(fake_llm_factory):
    """Assuntos completamente alheios (ex: futebol ou concorrentes) são rejeitados via regex."""
    fake_llm = fake_llm_factory()
    estado = {"pergunta_autonoma": "Qual foi o resultado do jogo de futebol de ontem?"}
    resultado = no_checa_escopo(estado, llm=fake_llm)

    assert resultado["dentro_escopo"] is False
    assert resultado["rota"] == "fora_escopo"
    assert len(fake_llm.historico_chamadas) == 0
    assert rota_pos_escopo(resultado) == "fora_escopo"


def test_no_checa_escopo_fallback_llm(fake_llm_factory):
    """Casos ambíguos sem termos óbvios acionam a classificação do LLM."""
    fake_llm = fake_llm_factory(resposta_padrao="DENTRO_ESCOPO")
    estado = {"pergunta_autonoma": "Como funciona a distribuição e perdas?"}
    resultado = no_checa_escopo(estado, llm=fake_llm)

    assert resultado["dentro_escopo"] is True


# ── Nó 4: Roteador de Consulta ───────────────────────────────────────────────
def test_no_roteador_consulta_rota_sql(fake_llm_factory):
    """Classificação estruturada direcionando para SQL com alta confiança."""
    resposta_json = '{"rota": "sql", "confianca": 0.95, "motivo": "Consulta de valores faturados"}'
    fake_llm = fake_llm_factory(resposta_padrao=resposta_json)
    estado = {"pergunta_autonoma": "Qual a receita total de 2023?", "chamadas_llm": 0}
    resultado = no_roteador_consulta(estado, llm=fake_llm)

    assert resultado["rota"] == "sql"
    assert resultado["confianca_rota"] == 0.95
    assert rota_pos_roteador(resultado) == "recupera_contexto"


def test_no_roteador_consulta_baixa_confianca_vira_recusa(fake_llm_factory):
    """Se a confiança do LLM for inferior a 0.60, deve acionar abstenção honesta automática."""
    resposta_json = '{"rota": "sql", "confianca": 0.45, "motivo": "Pergunta muito ambígua"}'
    fake_llm = fake_llm_factory(resposta_padrao=resposta_json)
    estado = {"pergunta_autonoma": "Quero ver coisas lá", "chamadas_llm": 0}
    resultado = no_roteador_consulta(estado, llm=fake_llm)

    assert resultado["rota"] == "recusa"
    assert rota_pos_roteador(resultado) == "recusa"


# ── Nó 7: Escrita de SQL ─────────────────────────────────────────────────────
def test_no_escreve_sql(fake_llm_factory):
    """Valida geração do SQL pelo LLM e incremento do contador de tentativas."""
    sql_retorno = "SELECT SUM(receita_faturada) FROM fact_faturamento WHERE ano = 2023"
    fake_llm = fake_llm_factory(resposta_padrao=sql_retorno)
    estado = {
        "pergunta_autonoma": "Qual a receita total de 2023?",
        "tentativas_sql": 0,
        "chamadas_llm": 0,
        "contexto_rag": [],
    }
    resultado = no_escreve_sql(estado, llm=fake_llm)

    assert resultado["sql_gerado"] == sql_retorno
    assert resultado["tentativas_sql"] == 1
    assert resultado["chamadas_llm"] == 1


# ── Nó 8: Validação de SQL ───────────────────────────────────────────────────
def test_no_valida_sql_aprovado():
    """Query legítima com tabelas permitidas deve ser aprovada para execução."""
    validador = StubValidadorSQL()
    estado = {
        "sql_gerado": "SELECT id_uc, receita_faturada FROM fact_faturamento WHERE ano = 2023",
        "tentativas_sql": 1,
    }
    resultado = no_valida_sql(estado, validador=validador)

    assert resultado["erro_validacao_ou_execucao"] is None
    assert resultado["malicioso"] is False
    assert rota_pos_validacao({**estado, **resultado}) == "executa"


def test_no_valida_sql_reprovado_ativa_retry():
    """Query que falha na validação em tentativa 1 deve acionar retry_sql."""
    validador = StubValidadorSQL()
    estado = {
        # Tabela não autorizada / inexistente
        "sql_gerado": "SELECT * FROM tb_usuarios_senhas",
        "tentativas_sql": 1,
    }
    resultado = no_valida_sql(estado, validador=validador)

    assert resultado["erro_validacao_ou_execucao"] is not None
    assert rota_pos_validacao({**estado, **resultado}) == "retry_sql"


def test_no_valida_sql_reprovado_esgotado_vira_recusa():
    """Query que falha na validação após atingir o teto de tentativas transiciona para recusa."""
    validador = StubValidadorSQL()
    estado = {
        "sql_gerado": "SELECT * FROM tb_usuarios_senhas",
        "tentativas_sql": 2,  # Teto atingido
    }
    resultado = no_valida_sql(estado, validador=validador)

    assert rota_pos_validacao({**estado, **resultado}) == "recusa"


# ── Nó 9: Execução de SQL ────────────────────────────────────────────────────
def test_no_executa_sql_sucesso(sql_executor_teste: SQLExecutor):
    """Executa query no SQLite sintético e preenche dados_sql no estado."""
    estado = {
        "sql_gerado": "SELECT COUNT(*) AS total FROM dim_unidade_consumidora",
        "tentativas_sql": 1,
    }
    resultado = no_executa_sql(estado, executor=sql_executor_teste)

    assert resultado["dados_sql"] is not None
    assert resultado["total_linhas_retornadas"] == 1
    assert resultado["erro_validacao_ou_execucao"] is None
    assert rota_pos_execucao({**estado, **resultado}) == "sintetiza"


def test_no_executa_sql_falha_ativa_retry(sql_executor_teste: SQLExecutor):
    """Query com erro de banco aciona retry_sql se ainda houver tentativas disponíveis."""
    estado = {
        "sql_gerado": "SELECT * FROM tabela_que_nao_existe",
        "tentativas_sql": 1,
    }
    resultado = no_executa_sql(estado, executor=sql_executor_teste)

    assert resultado["dados_sql"] is None
    assert resultado["erro_validacao_ou_execucao"] is not None
    assert rota_pos_execucao({**estado, **resultado}) == "retry_sql"


# ── Nó 10: Recusa Honesta ────────────────────────────────────────────────────
def test_no_recusa_honesta_fora_de_escopo():
    """Emite mensagem pedagógica para perguntas fora do escopo da concessão."""
    estado = {"rota": "fora_escopo", "malicioso": False}
    resultado = no_recusa_honesta(estado)

    assert "Região Metropolitana do Recife" in resultado["texto_resposta"]
    assert resultado["selo_confianca"] == "recusa_honesta"
    assert resultado["motivo_recusa"] == "fora_escopo"


def test_no_recusa_honesta_ataque_malicioso():
    """Emite recusa com selo de bloqueio para tentativas de ataque."""
    estado = {"rota": "bloqueio_seguranca", "malicioso": True}
    resultado = no_recusa_honesta(estado)

    assert "bloqueada por segurança" in resultado["texto_resposta"].lower()
    assert resultado["selo_confianca"] == "erro_bloqueado"
    assert resultado["motivo_recusa"] == "bloqueio_seguranca"


# ── Nó 11: Síntese de Resposta ───────────────────────────────────────────────
def test_no_sintetiza_resposta(fake_llm_factory):
    """Gera síntese narrativa em português com selo gerada_confiavel a partir de dados SQL."""
    texto_executivo = "Em 2023, o faturamento comercial em Olinda totalizou R$ 1.575,00."
    fake_llm = fake_llm_factory(resposta_padrao=texto_executivo)
    estado = {
        "pergunta_autonoma": "Qual o faturamento comercial em Olinda?",
        "rota": "sql",
        "dados_sql": [{"classe": "Comercial", "ano": 2023, "total_receita": 1575.0}],
        "contexto_rag": [],
        "chamadas_llm": 0,
        "hit_cache": False,
    }
    resultado = no_sintetiza_resposta(estado, llm=fake_llm)

    assert resultado["texto_resposta"] == texto_executivo
    assert resultado["selo_confianca"] == "gerada_confiavel"
    assert resultado["chamadas_llm"] == 1


# ── Nó 12: Finalização e Auditoria ───────────────────────────────────────────
def test_no_finaliza_auditoria():
    """Valida consolidação das métricas de latência e máscara de dados sensíveis."""
    estado = {
        "audit_id": "test-uuid-001",
        "pergunta_original": "Qual o faturamento?",
        "pergunta_autonoma": "Qual o faturamento?",
        "tempo_inicio_ts": 1000.0,
        "dados_sql": [{"nome": "Cliente Confidencial", "receita": 1250.0}],
    }
    resultado = no_finaliza_auditoria(estado, db_url=None)

    assert resultado["audit_id"] == "test-uuid-001"
    assert resultado["tempo_total_ms"] > 0
