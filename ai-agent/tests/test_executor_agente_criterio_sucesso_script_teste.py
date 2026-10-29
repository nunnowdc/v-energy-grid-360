"""
Testes para avaliar_resultado_teste_pipeline - critério de sucesso do script de teste manual.
Cobre todos os cenários de selo_confianca vs sql_gerado.
"""
from src.grafo.executor_agente import avaliar_resultado_teste_pipeline
from src.contratos.resposta_agente import RespostaAgente


class MockResposta:
    """Mock simples para testar sem depender do Pydantic completo."""
    def __init__(self, selo_confianca: str, sql_gerado: str | None = None):
        self.selo_confianca = selo_confianca
        self.sql_gerado = sql_gerado
        self.resposta_texto = "texto"
        self.dados_tabela = None
        self.fontes_citadas = []
        self.passos_executados = []
        self.hit_cache = False
        self.tempo_execucao_ms = 0.0
        self.tokens_totais = 0
        self.chamadas_llm = 0
        self.audit_id = "test"
        self.pergunta_original = "teste"
        self.pergunta_autonoma = "teste"


def test_documental_rag_sem_sql_retorna_codigo_0():
    """documental_rag sem SQL -> código 0 (sucesso, resposta documental não precisa de SQL)."""
    resposta = MockResposta(selo_confianca="documental_rag", sql_gerado=None)
    codigo, msg = avaliar_resultado_teste_pipeline(resposta)
    assert codigo == 0
    assert "documental" in msg.lower()
    assert "sucesso" in msg.lower()


def test_certificada_com_sql_retorna_codigo_0():
    """certificada com SQL -> código 0."""
    resposta = MockResposta(selo_confianca="certificada", sql_gerado="SELECT 1")
    codigo, msg = avaliar_resultado_teste_pipeline(resposta)
    assert codigo == 0
    assert "sucesso" in msg.lower()


def test_gerada_confiavel_com_sql_retorna_codigo_0():
    """gerada_confiavel com SQL -> código 0."""
    resposta = MockResposta(selo_confianca="gerada_confiavel", sql_gerado="SELECT 1")
    codigo, msg = avaliar_resultado_teste_pipeline(resposta)
    assert codigo == 0
    assert "sucesso" in msg.lower()


def test_certificada_sem_sql_retorna_codigo_1():
    """certificada sem SQL -> código 1 (erro: resposta baseada em dados requer SQL)."""
    resposta = MockResposta(selo_confianca="certificada", sql_gerado=None)
    codigo, msg = avaliar_resultado_teste_pipeline(resposta)
    assert codigo == 1
    assert "falha" in msg.lower()
    assert "sql" in msg.lower()


def test_gerada_confiavel_sem_sql_retorna_codigo_1():
    """gerada_confiavel sem SQL -> código 1 (erro: resposta baseada em dados requer SQL)."""
    resposta = MockResposta(selo_confianca="gerada_confiavel", sql_gerado=None)
    codigo, msg = avaliar_resultado_teste_pipeline(resposta)
    assert codigo == 1
    assert "falha" in msg.lower()
    assert "sql" in msg.lower()


def test_recusa_honesta_retorna_codigo_0_com_aviso():
    """recusa_honesta -> código 0 com mensagem de aviso (não é erro de execução)."""
    resposta = MockResposta(selo_confianca="recusa_honesta", sql_gerado=None)
    codigo, msg = avaliar_resultado_teste_pipeline(resposta)
    assert codigo == 0
    assert "aviso" in msg.lower()
    assert "recusou" in msg.lower()


def test_erro_bloqueado_retorna_codigo_1():
    """erro_bloqueado -> código 1 (falha real de execução)."""
    resposta = MockResposta(selo_confianca="erro_bloqueado", sql_gerado=None)
    codigo, msg = avaliar_resultado_teste_pipeline(resposta)
    assert codigo == 1
    assert "falha" in msg.lower()
    assert "concluir" in msg.lower()


def test_selo_desconhecido_retorna_codigo_0():
    """Selo desconhecido (futuro) -> código 0 por padrão (fail-open para não quebrar testes)."""
    resposta = MockResposta(selo_confianca="novo_selo_futuro", sql_gerado=None)
    codigo, msg = avaliar_resultado_teste_pipeline(resposta)
    assert codigo == 0
    assert "sucesso" in msg.lower()