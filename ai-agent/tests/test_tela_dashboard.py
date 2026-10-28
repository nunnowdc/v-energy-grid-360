"""
Testes da escolha da tela do portal a partir do SQL executado e do resultado.
Valores fictícios; nenhum dado vem da base real.
"""
from __future__ import annotations

import pytest

from src.services.tela_dashboard import tela_do_dashboard


def _filtros(tela) -> dict:
    return tela.filtros.model_dump(exclude_none=True)


def test_cache_certificado_abre_indicadores_com_o_municipio():
    sql = (
        "SELECT r.municipio, r.ano, SUM(r.receita_faturada) AS receita_total "
        "FROM agg_receita_mensal r "
        "WHERE unaccent(lower(r.municipio)) = unaccent(lower('recife')) AND r.ano = 2024 "
        "GROUP BY r.municipio, r.ano"
    )
    tela = tela_do_dashboard(sql, [{"municipio": "Recife", "ano": 2024, "receita_total": 10.0}])
    assert tela.tela == "indicadores"
    # O WHERE vale mais que a linha do resultado
    assert _filtros(tela) == {"municipio": "recife"}


def test_variacao_de_receita_abre_receita_com_bairro_e_classe():
    sql = (
        "SELECT SUM(efeito_preco) FROM agg_receita_preco_volume "
        "WHERE unaccent(lower(municipio)) = unaccent(lower('Olinda')) "
        "AND (unaccent(lower(bairro)) = unaccent(lower('Centro')) AND classe IN ('COMERCIAL'))"
    )
    tela = tela_do_dashboard(sql, [{"sum": 1.0}])
    assert tela.tela == "receita"
    assert _filtros(tela) == {"municipio": "Olinda", "bairro": "Centro", "classe": "COMERCIAL"}


def test_maior_dec_pega_o_alimentador_da_linha_unica():
    sql = (
        "SELECT alimentador, municipio_principal, dec FROM agg_continuidade_alimentador_anual "
        "WHERE ano = 2025 ORDER BY dec DESC LIMIT 1"
    )
    tela = tela_do_dashboard(sql, [{"alimentador": "ALM-REC-008", "municipio_principal": "Recife", "dec": 9.1}])
    assert tela.tela == "continuidade"
    assert _filtros(tela) == {"alimentador": "ALM-REC-008", "municipio": "Recife"}


def test_ranking_com_varias_linhas_nao_escolhe_um_valor():
    sql = "SELECT alimentador, dec FROM agg_continuidade_alimentador_anual WHERE ano = 2025 ORDER BY dec DESC LIMIT 5"
    dados = [{"alimentador": "ALM-REC-008", "dec": 9.1}, {"alimentador": "ALM-OLI-002", "dec": 8.7}]
    tela = tela_do_dashboard(sql, dados)
    assert tela.tela == "continuidade"
    assert _filtros(tela) == {}


def test_causa_em_ocorrencias_abre_continuidade():
    sql = (
        "SELECT COUNT(*) FROM fact_ocorrencias o JOIN dim_unidade_consumidora u ON o.id_uc = u.id_uc "
        "WHERE unaccent(lower(o.causa)) = unaccent(lower('climatica'))"
    )
    tela = tela_do_dashboard(sql, [{"count": 3}])
    # Continuidade tem prioridade sobre o cadastro de UCs
    assert tela.tela == "continuidade"
    assert _filtros(tela) == {"causa": "climatica"}


def test_uc_filtrada_abre_a_visao_360():
    sql = "SELECT competencia, receita_faturada FROM fact_faturamento WHERE id_uc = 'UC100000'"
    tela = tela_do_dashboard(sql, [{"competencia": "2025-01-01"}, {"competencia": "2025-02-01"}])
    assert tela.tela == "visao_360"
    assert _filtros(tela) == {"id_uc": "UC100000"}


def test_uc_mais_suspeita_abre_a_visao_360_dela():
    sql = "SELECT id_uc, score FROM fila_inspecao ORDER BY prioridade LIMIT 1"
    tela = tela_do_dashboard(sql, [{"id_uc": "UC100001", "score": 90}])
    assert tela.tela == "visao_360"
    assert _filtros(tela) == {"id_uc": "UC100001"}


def test_lista_de_suspeitas_abre_a_fila():
    sql = (
        "SELECT id_uc, score FROM fila_inspecao "
        "WHERE unaccent(lower(municipio)) = unaccent(lower('olinda')) ORDER BY prioridade LIMIT 10"
    )
    tela = tela_do_dashboard(sql, [{"id_uc": "UC100001"}, {"id_uc": "UC100002"}])
    assert tela.tela == "inspecoes"
    assert _filtros(tela) == {"municipio": "olinda"}


@pytest.mark.parametrize(
    "where",
    [
        "unaccent(lower(municipio)) = 'recife' OR unaccent(lower(municipio)) = 'olinda'",
        "unaccent(lower(municipio)) IN ('recife', 'olinda')",
        "municipio = 'Recife' AND municipio = 'Olinda'",
        "municipio <> 'Recife'",
        "municipio LIKE '%Rec%'",
    ],
)
def test_filtro_com_mais_de_um_valor_ou_sem_igualdade_fica_de_fora(where):
    tela = tela_do_dashboard(f"SELECT SUM(consumo_kwh) FROM agg_receita_mensal WHERE {where}", [])
    assert tela.tela == "indicadores"
    assert _filtros(tela) == {}


def test_mesmo_valor_com_grafia_diferente_conta_como_um():
    sql = (
        "SELECT COUNT(*) FROM dim_unidade_consumidora "
        "WHERE municipio = 'Jaboatão dos Guararapes' AND unaccent(lower(municipio)) = 'jaboatao dos guararapes'"
    )
    assert _filtros(tela_do_dashboard(sql, [])) == {"municipio": "Jaboatão dos Guararapes"}


def test_filtro_dentro_de_subconsulta_tambem_vale():
    sql = (
        "SELECT AVG(dec) FROM agg_continuidade_alimentador WHERE alimentador IN "
        "(SELECT alimentador FROM dim_unidade_consumidora WHERE unaccent(lower(municipio)) = 'paulista')"
    )
    tela = tela_do_dashboard(sql, [{"avg": 1.0}])
    assert tela.tela == "continuidade"
    assert _filtros(tela) == {"municipio": "paulista"}


def test_case_when_nao_vira_filtro():
    sql = (
        "SELECT SUM(CASE WHEN classe = 'RURAL' THEN consumo_kwh ELSE 0 END) "
        "FROM agg_receita_mensal WHERE ano = 2024"
    )
    assert _filtros(tela_do_dashboard(sql, [{"sum": 1.0}])) == {}


@pytest.mark.parametrize(
    "sql",
    [
        None,
        "",
        "SQL_INDISPONIVEL",
        "SELECT * FROM",
        "SELECT AVG(tempo_resolucao_h) FROM fact_atendimentos",
    ],
)
def test_sem_consulta_legivel_ou_sem_tela_no_portal_nao_muda_a_tela(sql):
    assert tela_do_dashboard(sql, [{"avg": 1.0}]) is None
