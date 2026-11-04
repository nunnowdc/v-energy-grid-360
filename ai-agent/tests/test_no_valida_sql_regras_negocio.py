"""O nó 8 devolve ao LLM o SQL válido com conta errada, e só registra na última tentativa."""
from src.interfaces.stub_validador_sql import StubValidadorSQL
from src.nos.no_valida_sql import MAX_TENTATIVAS, no_valida_sql, rota_pos_validacao

SQL_SOMA_PCT = "SELECT municipio, bairro, SUM(variacao_volume_pct) FROM agg_receita_preco_volume GROUP BY municipio, bairro"


def test_conta_errada_volta_para_nova_tentativa():
    estado = {"sql_gerado": SQL_SOMA_PCT, "tentativas_sql": 1}
    resultado = no_valida_sql(estado, validador=StubValidadorSQL())
    assert "Regras de negócio" in resultado["erro_validacao_ou_execucao"]
    assert rota_pos_validacao({**estado, **resultado}) == "retry_sql"


def test_na_ultima_tentativa_executa_com_aviso():
    estado = {"sql_gerado": SQL_SOMA_PCT, "tentativas_sql": MAX_TENTATIVAS}
    resultado = no_valida_sql(estado, validador=StubValidadorSQL())
    assert resultado["erro_validacao_ou_execucao"] is None
    assert any("aviso" in passo for passo in resultado["passos_executados"])
    assert rota_pos_validacao({**estado, **resultado}) == "executa"
