"""Conferência somente leitura dos indicadores HTTP contra a Gold local."""

from datetime import date
from itertools import pairwise

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import get_connection
from app.main import app


def _month_at(index: int) -> date:
    return date(index // 12, index % 12 + 1, 1)


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
@pytest.mark.parametrize("size", [3, 6, 12])
def test_indicadores_http_conciliam_com_agregacoes_gold(size: int) -> None:
    with get_connection() as connection:
        last = connection.execute(
            text("SELECT MAX(competencia) FROM dim_competencia")
        ).scalar_one()
        start = _month_at(last.year * 12 + last.month - 1 - size + 1)
        previous_start = _month_at(start.year * 12 + start.month - 1 - size)
        previous_end = _month_at(start.year * 12 + start.month - 2)
        classes_gold = (
            connection.execute(
                text(
                    "SELECT DISTINCT classe FROM dim_unidade_consumidora ORDER BY classe"
                )
            )
            .scalars()
            .all()
        )
        expected = {}
        for name, begin, end in (
            ("atual", start, last),
            ("anterior", previous_start, previous_end),
        ):
            totals = connection.execute(
                text(
                    "SELECT SUM(receita_faturada) AS receita, "
                    "SUM(consumo_kwh) AS consumo, SUM(faturas) AS faturas, "
                    "SUM(faturas_atrasadas) AS atrasadas "
                    "FROM agg_receita_mensal "
                    "WHERE competencia BETWEEN :inicio AND :fim"
                ),
                {"inicio": begin, "fim": end},
            ).one()
            ucs = connection.execute(
                text(
                    "SELECT SUM(ucs_faturadas) FROM agg_receita_mensal "
                    "WHERE competencia = :fim"
                ),
                {"fim": end},
            ).scalar_one()
            expected[name] = (totals, ucs)

    response = TestClient(app).get(
        "/api/metrics/general",
        params={"inicio": start.strftime("%Y-%m"), "fim": last.strftime("%Y-%m")},
    )
    assert response.status_code == 200
    body = response.json()
    for name in ("atual", "anterior"):
        totals, ucs = expected[name]
        assert body[name]["receita_faturada"] == pytest.approx(totals.receita, rel=1e-8)
        assert body[name]["consumo_kwh"] == pytest.approx(totals.consumo, rel=1e-8)
        assert body[name]["faturas"] == totals.faturas
        assert body[name]["faturas_atrasadas"] == totals.atrasadas
        assert body[name]["ucs_faturadas"] == ucs
        assert sum(
            row["receita_faturada"] or 0 for row in body["mensal"][name]
        ) == pytest.approx(totals.receita, rel=1e-8)
    assert [row["classe"] for row in body["por_classe"]] == classes_gold
    assert len(body["mensal"]["atual"]) == size
    assert len(body["mensal"]["anterior"]) == size
    assert sum(
        row["receita_faturada"] or 0 for row in body["por_classe"]
    ) == pytest.approx(body["atual"]["receita_faturada"], rel=1e-8)


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
@pytest.mark.parametrize("size", [3, 6, 12])
@pytest.mark.parametrize("filter_kind", ["municipio", "classe", "ambos"])
def test_indicadores_filtrados_conciliam_com_gold_local(
    size: int, filter_kind: str
) -> None:
    with get_connection() as connection:
        last = connection.execute(
            text("SELECT MAX(competencia) FROM dim_competencia")
        ).scalar_one()
        start = _month_at(last.year * 12 + last.month - size)
        previous_start = _month_at(start.year * 12 + start.month - 1 - size)
        previous_end = _month_at(start.year * 12 + start.month - 2)
        municipio, classe = connection.execute(
            text(
                "SELECT municipio, classe FROM agg_receita_mensal "
                "GROUP BY municipio, classe "
                "ORDER BY COUNT(*) DESC, municipio, classe LIMIT 1"
            )
        ).one()

        filters = {}
        clauses = ""
        if filter_kind in {"municipio", "ambos"}:
            filters["municipio"] = municipio
            clauses += " AND municipio = :municipio"
        if filter_kind in {"classe", "ambos"}:
            filters["classe"] = classe
            clauses += " AND classe = :classe"

        expected = {}
        for name, begin, end in (
            ("atual", start, last),
            ("anterior", previous_start, previous_end),
        ):
            params = {"inicio": begin, "fim": end, **filters}
            totals = connection.execute(
                text(
                    "SELECT SUM(receita_faturada) AS receita, "
                    "SUM(consumo_kwh) AS consumo, SUM(faturas) AS faturas, "
                    "SUM(faturas_atrasadas) AS atrasadas "
                    "FROM agg_receita_mensal "
                    f"WHERE competencia BETWEEN :inicio AND :fim{clauses}"
                ),
                params,
            ).one()
            ucs = connection.execute(
                text(
                    "SELECT SUM(ucs_faturadas) FROM agg_receita_mensal "
                    f"WHERE competencia = :fim{clauses}"
                ),
                params,
            ).scalar_one()
            monthly = connection.execute(
                text(
                    "SELECT competencia, SUM(receita_faturada) AS receita, "
                    "SUM(consumo_kwh) AS consumo FROM agg_receita_mensal "
                    f"WHERE competencia BETWEEN :inicio AND :fim{clauses} "
                    "GROUP BY competencia"
                ),
                params,
            ).all()
            by_class = connection.execute(
                text(
                    "SELECT classe, SUM(receita_faturada) AS receita "
                    "FROM agg_receita_mensal "
                    f"WHERE competencia BETWEEN :inicio AND :fim{clauses} "
                    "GROUP BY classe"
                ),
                params,
            ).all()
            expected[name] = (totals, ucs, monthly, by_class)

    response = TestClient(app).get(
        "/api/metrics/general",
        params={
            "inicio": start.strftime("%Y-%m"),
            "fim": last.strftime("%Y-%m"),
            **filters,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"atual", "anterior", "mensal", "por_classe"}

    for name in ("atual", "anterior"):
        totals, ucs, monthly, by_class = expected[name]
        assert body[name]["receita_faturada"] == pytest.approx(totals.receita, rel=1e-8)
        assert body[name]["consumo_kwh"] == pytest.approx(totals.consumo, rel=1e-8)
        assert body[name]["faturas"] == totals.faturas
        assert body[name]["faturas_atrasadas"] == totals.atrasadas
        assert body[name]["ucs_faturadas"] == ucs
        if totals.consumo is not None and totals.consumo > 0:
            assert body[name]["preco_medio_kwh"] == pytest.approx(
                totals.receita / totals.consumo, rel=1e-8
            )
        else:
            assert body[name]["preco_medio_kwh"] is None

        monthly_by_date = {row.competencia: row for row in monthly}
        assert len(body["mensal"][name]) == size
        for point in body["mensal"][name]:
            competence = date.fromisoformat(f"{point['mes_referencia']}-01")
            gold_row = monthly_by_date.get(competence)
            if gold_row is None:
                assert point["receita_faturada"] is None
                assert point["consumo_kwh"] is None
            else:
                assert point["receita_faturada"] == pytest.approx(
                    gold_row.receita, rel=1e-8
                )
                assert point["consumo_kwh"] == pytest.approx(gold_row.consumo, rel=1e-8)

        field = "receita_faturada" if name == "atual" else "receita_faturada_anterior"
        expected_classes = {row.classe: row.receita for row in by_class}
        for item in body["por_classe"]:
            expected_revenue = expected_classes.get(item["classe"])
            if expected_revenue is None:
                assert item[field] is None
            else:
                assert item[field] == pytest.approx(expected_revenue, rel=1e-8)
    assert len(body["por_classe"]) == (1 if "classe" in filters else 5)


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_integridade_calendario_e_grao_gold_local() -> None:
    """Consulta somente leitura; não fixa totais dependentes do snapshot."""
    with get_connection() as connection:
        calendar = connection.execute(
            text(
                "SELECT competencia, mes_referencia FROM dim_competencia "
                "ORDER BY competencia"
            )
        ).all()
        counts = connection.execute(
            text(
                "SELECT COUNT(*) AS total, "
                "COUNT(DISTINCT (competencia, municipio, bairro, classe, possui_gd)) "
                "AS unicas FROM agg_receita_mensal"
            )
        ).one()

    assert len(calendar) >= 24
    assert len(calendar) == len({row.competencia for row in calendar})
    assert all(
        row.competencia.day == 1
        and row.mes_referencia == row.competencia.strftime("%Y-%m")
        for row in calendar
    )
    assert all(
        right.competencia.year * 12
        + right.competencia.month
        - (left.competencia.year * 12 + left.competencia.month)
        == 1
        for left, right in pairwise(calendar)
    )
    assert counts.total == counts.unicas
