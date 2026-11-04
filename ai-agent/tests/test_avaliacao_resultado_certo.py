"""O golden set confere o RESULTADO do agente com o do sql_esperado, não só as tabelas."""
from src.avaliacao.golden_set import avaliar_caso, comparar_resultado, executar_avaliacao, resumir
from src.contratos.resposta_agente import RespostaAgente

CASO = {
    "id": "TC-006",
    "pergunta": "Qual a receita média faturada por cliente residencial em Recife em 2023?",
    "rota_esperada": "sql",
    "sql_esperado": "SELECT 1",
    "tabelas_obrigatorias": ["agg_receita_mensal"],
    "deve_recusar": False,
}
ESPERADO = [{"receita_media_por_cliente": 1584.1769536423549}]


def _resposta(dados):
    return RespostaAgente(
        audit_id="x",
        pergunta_original=CASO["pergunta"],
        pergunta_autonoma=CASO["pergunta"],
        resposta_texto="...",
        sql_gerado="SELECT SUM(receita_faturada) / NULLIF(SUM(ucs_faturadas), 0) FROM agg_receita_mensal",
        dados_tabela=dados,
        selo_confianca="gerada_confiavel",
    )


def test_compara_ignorando_nome_da_coluna_arredondamento_e_colunas_a_mais():
    assert comparar_resultado(ESPERADO, [{"outro_nome": 1584.18, "extra": 7}]) == []
    assert comparar_resultado(ESPERADO, [{"receita": 132.15}]) == [1584.1769536423549]


def test_valor_pequeno_errado_nao_passa_pela_tolerancia():
    # TC-016: preço do kWh. AVG(preco_medio_kwh) dá 0,8065; o certo é 0,7978
    esperado = [{"preco_medio_kwh": 0.7978}]
    assert comparar_resultado(esperado, [{"p": 0.8065}]) == [0.7978]
    # O arredondamento do agente continua aceito
    assert comparar_resultado(esperado, [{"p": 0.80}]) == []


def test_sem_numeros_confere_o_texto_sem_acento():
    esperado = [{"municipio": "Jaboatão dos Guararapes"}]
    assert comparar_resultado(esperado, [{"m": "Jaboatao dos Guararapes"}]) == []
    assert comparar_resultado(esperado, [{"m": "Recife"}]) == ["jaboatao dos guararapes"]


def test_esperado_vazio_nao_tem_o_que_conferir():
    assert comparar_resultado([], [{"r": 1}]) is None
    assert comparar_resultado([{"x": None}], [{"r": 1}]) is None


def test_sql_valido_com_tabela_certa_e_numero_errado_reprova():
    # O que acontecia no TC-006: tabela "certa", média mensal no lugar da anual
    resultado = avaliar_caso(CASO, _resposta([{"r": 132.15}]), ESPERADO)
    assert resultado["tabelas_certas"] is True
    assert resultado["resultado_certo"] is False
    assert resultado["passou"] is False
    assert "não bate" in resultado["motivo"]


def test_numero_certo_aprova():
    resultado = avaliar_caso(CASO, _resposta([{"r": 1584.18}]), ESPERADO)
    assert resultado["resultado_certo"] is True and resultado["passou"] is True


def test_sem_resultado_esperado_fica_o_criterio_das_tabelas():
    resultado = avaliar_caso(CASO, _resposta([{"r": 132.15}]))
    assert resultado["resultado_certo"] is None and resultado["passou"] is True


def test_esperado_vazio_ou_com_erro_fica_nao_conferido_e_avisa():
    vazio = avaliar_caso(CASO, _resposta([{"r": 132.15}]), [])
    com_erro = avaliar_caso(CASO, _resposta([{"r": 132.15}]), None, "relation x does not exist")
    for resultado in (vazio, com_erro):
        assert resultado["resultado_certo"] is None
        assert "NÃO conferido" in resultado["motivo"]


def test_execucao_roda_o_sql_esperado_e_resume_a_taxa():
    sqls = []

    def esperado(sql):
        sqls.append(sql)
        return ESPERADO

    execucao = executar_avaliacao(
        [CASO], lambda **_: _resposta([{"r": 132.15}]), executar_esperado=esperado
    )
    assert sqls == ["SELECT 1"]
    assert execucao["taxa_resultado_certo"] == 0.0
    assert resumir([])["taxa_resultado_certo"] is None


def test_sql_esperado_quebrado_nao_derruba_a_rodada():
    def esperado(_sql):
        raise RuntimeError("syntax error")

    execucao = executar_avaliacao(
        [CASO, CASO], lambda **_: _resposta([{"r": 1584.18}]), executar_esperado=esperado
    )
    assert len(execucao["casos"]) == 2
    assert all("NÃO conferido" in caso["motivo"] for caso in execucao["casos"])
    # Nenhum caso conferido: a taxa fica nula, não 100%
    assert execucao["taxa_resultado_certo"] is None
