"""Avaliação do golden set gravada para a tela do Admin TI (src/avaliacao)."""

from __future__ import annotations

from typing import Any

import pytest
from src.avaliacao.armazenamento import gravar_execucao
from src.avaliacao.golden_set import (
    avaliar_caso,
    carregar_casos,
    executar_avaliacao,
    resumir,
)
from src.contratos.resposta_agente import RespostaAgente

CASO_SQL = {
    "id": "TC-001",
    "pergunta": "Qual o faturamento total da classe comercial em Olinda no ano de 2023?",
    "rota_esperada": "sql",
    "deve_recusar": False,
    "tabelas_obrigatorias": ["fact_faturamento", "dim_unidade_consumidora"],
}
CASO_RAG = {
    "id": "TC-007",
    "pergunta": "Como a ANEEL define o DEC?",
    "rota_esperada": "rag",
    "deve_recusar": False,
    "tabelas_obrigatorias": [],
}
CASO_RECUSA = {
    "id": "TC-012",
    "pergunta": "Quem ganhou o jogo ontem?",
    "rota_esperada": "recusa",
    "deve_recusar": True,
    "tabelas_obrigatorias": [],
}

SQL_CERTO = (
    "SELECT SUM(f.receita_faturada) FROM fact_faturamento f "
    "JOIN dim_unidade_consumidora u ON f.id_uc = u.id_uc WHERE u.municipio = 'Olinda'"
)


def resposta(
    selo: str, sql: str | None = None, dados: list | None = None, tokens: int = 100
) -> RespostaAgente:
    return RespostaAgente(
        audit_id="a1",
        pergunta_original="p",
        pergunta_autonoma="p",
        resposta_texto="r",
        sql_gerado=sql,
        dados_tabela=dados,
        selo_confianca=selo,
        tokens_totais=tokens,
        tempo_execucao_ms=1500.0,
    )


@pytest.mark.parametrize("selo", ["gerada_confiavel", "certificada"])
def test_consulta_que_roda_com_as_tabelas_esperadas_passa(selo):
    resultado = avaliar_caso(CASO_SQL, resposta(selo, SQL_CERTO, [{"total": 1.0}]))

    assert resultado["passou"] is True
    assert resultado["executou"] is True
    assert resultado["tabelas_certas"] is True
    assert resultado["motivo"] == "Rodou a consulta com as tabelas esperadas"
    assert resultado["tipo"] == "sql"


def test_consulta_que_roda_em_outra_tabela_falha_e_diz_qual_faltou():
    sql = "SELECT SUM(receita_faturada) FROM agg_receita_mensal WHERE municipio = 'Olinda'"
    resultado = avaliar_caso(
        CASO_SQL, resposta("gerada_confiavel", sql, [{"total": 1.0}])
    )

    assert resultado["passou"] is False
    assert resultado["executou"] is True
    assert resultado["tabelas_certas"] is False
    assert (
        resultado["motivo"]
        == "Rodou, mas sem a tabela esperada: dim_unidade_consumidora, fact_faturamento"
    )


def test_consulta_que_nao_roda_falha_mesmo_com_o_sql_certo():
    resultado = avaliar_caso(CASO_SQL, resposta("recusa_honesta", SQL_CERTO, None))

    assert resultado["passou"] is False
    assert resultado["executou"] is False
    assert resultado["tabelas_certas"] is True
    assert resultado["motivo"] == "A consulta não rodou (selo recusa_honesta)"


def test_documentos_e_recusas_seguem_o_selo():
    assert avaliar_caso(CASO_RAG, resposta("documental_rag"))["passou"] is True
    rag_errado = avaliar_caso(CASO_RAG, resposta("recusa_honesta"))
    assert rag_errado["passou"] is False
    assert (
        rag_errado["motivo"] == "Não respondeu com os documentos (selo recusa_honesta)"
    )
    assert rag_errado["executou"] is None

    assert (
        avaliar_caso(CASO_RECUSA, resposta("recusa_honesta"))["motivo"]
        == "Recusou, como esperado"
    )
    assert avaliar_caso(CASO_RECUSA, resposta("erro_bloqueado"))["passou"] is True
    respondeu = avaliar_caso(CASO_RECUSA, resposta("gerada_confiavel"))
    assert respondeu["passou"] is False
    assert (
        respondeu["motivo"] == "Respondeu quando devia recusar (selo gerada_confiavel)"
    )


def test_resumo_calcula_as_quatro_metricas_por_tipo_de_caso():
    resultados = [
        avaliar_caso(CASO_SQL, resposta("certificada", SQL_CERTO, [{}], tokens=1000)),
        avaliar_caso(
            CASO_SQL,
            resposta(
                "gerada_confiavel",
                "SELECT 1 FROM agg_receita_mensal",
                [{}],
                tokens=2000,
            ),
        ),
        avaliar_caso(CASO_SQL, resposta("recusa_honesta", None, None, tokens=300)),
        avaliar_caso(
            CASO_SQL, resposta("gerada_confiavel", SQL_CERTO, [{}], tokens=1700)
        ),
        avaliar_caso(CASO_RAG, resposta("documental_rag", tokens=500)),
        avaliar_caso(CASO_RECUSA, resposta("recusa_honesta", tokens=0)),
        avaliar_caso(CASO_RECUSA, resposta("gerada_confiavel", tokens=500)),
    ]

    assert resumir(resultados) == {
        "total_casos": 7,
        "casos_aprovados": 4,
        # 3 das 4 consultas rodaram; 2 das 4 com as tabelas esperadas
        "taxa_execucao": 75.0,
        "taxa_component_match": 50.0,
        # 1 das 2 recusas
        "taxa_abstencao": 50.0,
        "tokens_medio": 6000 / 7,
    }


def test_resumo_sem_casos_de_um_tipo_deixa_a_metrica_nula():
    resumo = resumir([avaliar_caso(CASO_RAG, resposta("documental_rag"))])

    assert resumo["taxa_execucao"] is None
    assert resumo["taxa_component_match"] is None
    assert resumo["taxa_abstencao"] is None
    assert resumo["casos_aprovados"] == 1
    assert resumir([])["tokens_medio"] is None


def test_execucao_pergunta_cada_caso_sem_gravar_na_auditoria():
    chamadas: list[dict[str, Any]] = []
    terminados: list[str] = []

    def executar(**kwargs):
        chamadas.append(kwargs)
        return (
            resposta("recusa_honesta")
            if "jogo" in kwargs["pergunta"]
            else resposta("documental_rag")
        )

    execucao = executar_avaliacao(
        [CASO_RAG, CASO_RECUSA],
        executar,
        ao_terminar_caso=lambda c: terminados.append(c["caso_id"]),
    )

    assert chamadas == [
        {
            "pergunta": CASO_RAG["pergunta"],
            "sessao_id": "golden-TC-007",
            "persistir_auditoria": False,
        },
        {
            "pergunta": CASO_RECUSA["pergunta"],
            "sessao_id": "golden-TC-012",
            "persistir_auditoria": False,
        },
    ]
    assert terminados == ["TC-007", "TC-012"]
    assert execucao["casos_aprovados"] == 2
    assert [caso["caso_id"] for caso in execucao["casos"]] == ["TC-007", "TC-012"]
    assert execucao["duracao_ms"] >= 0


def test_golden_set_do_repositorio_tem_os_campos_usados_na_avaliacao():
    casos = carregar_casos()

    assert len(casos) >= 10
    for caso in casos:
        assert {
            "id",
            "pergunta",
            "rota_esperada",
            "deve_recusar",
            "tabelas_obrigatorias",
        } <= caso.keys()
        assert caso["rota_esperada"] in {"sql", "rag", "recusa"}


class CursorFalso:
    def __init__(self, banco):
        self.banco = banco

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.banco.comandos.append((" ".join(sql.split()), params))

    def fetchone(self):
        return ("11111111-1111-4111-8111-111111111111",)


class ConexaoFalsa:
    def __init__(self):
        self.comandos: list = []
        self.commits = 0

    def cursor(self):
        return CursorFalso(self)

    def commit(self):
        self.commits += 1


def test_gravacao_cria_as_tabelas_e_grava_execucao_e_casos_numa_transacao():
    execucao = executar_avaliacao(
        [CASO_SQL, CASO_RECUSA],
        lambda **kw: resposta("gerada_confiavel", SQL_CERTO, [{}], tokens=900),
    )
    conexao = ConexaoFalsa()

    avaliacao_id = gravar_execucao(conexao, execucao, "modelo-x")

    assert avaliacao_id == "11111111-1111-4111-8111-111111111111"
    assert conexao.commits == 1
    ddl, execucao_sql, *casos_sql = conexao.comandos
    assert "CREATE TABLE IF NOT EXISTS tb_avaliacoes_agente" in ddl[0]
    assert execucao_sql[0].startswith("INSERT INTO tb_avaliacoes_agente (modelo,")
    assert execucao_sql[1][:3] == ["modelo-x", 2, 1]
    assert len(casos_sql) == 2
    assert casos_sql[1][1][:6] == [
        "11111111-1111-4111-8111-111111111111",
        "TC-012",
        "recusa",
        CASO_RECUSA["pergunta"],
        "gerada_confiavel",
        False,
    ]
