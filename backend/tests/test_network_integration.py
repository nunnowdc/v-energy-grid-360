"""Conciliação somente leitura da resposta padrão com a Gold local."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import bindparam, text

from app.core.config import get_settings
from app.core.database import get_connection
from app.main import app


def _month_at(index: int) -> date:
    return date(index // 12, index % 12 + 1, 1)


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_continuidade_padrao_concilia_com_gold_local() -> None:
    with get_connection() as connection:
        last = connection.execute(
            text("SELECT MAX(competencia) FROM dim_competencia")
        ).scalar_one()
        if last is None:
            pytest.skip("Calendário Gold local vazio")
        last_index = last.year * 12 + last.month - 1
        current_start = _month_at(last_index - 11)
        previous_start = _month_at(last_index - 23)
        previous_end = _month_at(last_index - 12)
        expected = connection.execute(
            text(
                "SELECT alimentador, SUM(dec) AS dec, SUM(fec) AS fec, "
                "SUM(dec_sem_dia_critico) AS dec_sem_dia_critico "
                "FROM agg_continuidade_alimentador "
                "WHERE competencia BETWEEN :inicio AND :fim "
                "GROUP BY alimentador ORDER BY dec DESC, alimentador ASC"
            ),
            {"inicio": current_start, "fim": last},
        ).all()
        assert expected
        first = expected[0]
        previous_dec = connection.execute(
            text(
                "SELECT SUM(dec) FROM agg_continuidade_alimentador "
                "WHERE alimentador = :alimentador "
                "AND competencia BETWEEN :inicio AND :fim"
            ),
            {
                "alimentador": first.alimentador,
                "inicio": previous_start,
                "fim": previous_end,
            },
        ).scalar_one()
        occurrences = connection.execute(
            text(
                "SELECT causa, COUNT(*) AS quantidade FROM fact_ocorrencias "
                "WHERE competencia BETWEEN :inicio AND :fim "
                "GROUP BY causa ORDER BY quantidade DESC, causa ASC"
            ),
            {"inicio": current_start, "fim": last},
        ).all()

    response = TestClient(app).get("/api/network/continuity")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["periodo"] == {
        "inicio": current_start.strftime("%Y-%m"),
        "fim": last.strftime("%Y-%m"),
    }
    assert body["periodo_anterior"] == {
        "inicio": previous_start.strftime("%Y-%m"),
        "fim": previous_end.strftime("%Y-%m"),
    }
    assert [row["alimentador"] for row in body["ranking"]] == [
        row.alimentador for row in expected
    ]
    top = body["ranking"][0]
    assert top["dec"] == pytest.approx(first.dec, abs=0.5e-6)
    assert top["fec"] == pytest.approx(first.fec, abs=0.5e-6)
    assert top["dec_sem_dia_critico"] == pytest.approx(
        first.dec_sem_dia_critico, abs=0.5e-6
    )
    assert top["dec_anterior"] == pytest.approx(previous_dec, abs=0.5e-6)
    assert body["serie"]["alimentador"] == first.alimentador
    assert len(body["serie"]["atual"]) == 12
    assert len(body["serie"]["anterior"]) == 12
    assert body["ocorrencias"]["total"] == sum(row.quantidade for row in occurrences)
    assert body["ocorrencias"]["por_causa"] == [
        {"causa": row.causa, "ocorrencias": row.quantidade} for row in occurrences
    ]


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
@pytest.mark.parametrize("size", [1, 3, 24])
def test_periodos_escolhidos_conciliam_com_gold_local(size: int) -> None:
    with get_connection() as connection:
        months = (
            connection.execute(
                text("SELECT competencia FROM dim_competencia ORDER BY competencia")
            )
            .scalars()
            .all()
        )
        if len(months) < size * 2:
            pytest.skip("Calendário Gold local sem cobertura para o teste")
        previous_start, previous_end = months[0], months[size - 1]
        current_start, current_end = months[-size], months[-1]
        if previous_end >= current_start:
            pytest.skip("Calendário Gold local sem janelas disjuntas")
        expected = connection.execute(
            text(
                "SELECT alimentador, SUM(dec) AS dec "
                "FROM agg_continuidade_alimentador "
                "WHERE competencia BETWEEN :inicio AND :fim "
                "GROUP BY alimentador ORDER BY dec DESC, alimentador ASC LIMIT 1"
            ),
            {"inicio": current_start, "fim": current_end},
        ).one()
        expected_previous_dec = connection.execute(
            text(
                "SELECT SUM(dec) FROM agg_continuidade_alimentador "
                "WHERE alimentador = :alimentador "
                "AND competencia BETWEEN :inicio AND :fim"
            ),
            {
                "alimentador": expected.alimentador,
                "inicio": previous_start,
                "fim": previous_end,
            },
        ).scalar_one()
        expected_occurrences = {}
        for name, start, end in (
            ("base", previous_start, previous_end),
            ("comparado", current_start, current_end),
        ):
            expected_occurrences[name] = connection.execute(
                text(
                    "SELECT COUNT(*) FROM fact_ocorrencias "
                    "WHERE competencia BETWEEN :inicio AND :fim"
                ),
                {"inicio": start, "fim": end},
            ).scalar_one()

    response = TestClient(app).get(
        "/api/network/continuity",
        params={
            "inicio": current_start.strftime("%Y-%m"),
            "fim": current_end.strftime("%Y-%m"),
            "inicio_anterior": previous_start.strftime("%Y-%m"),
            "fim_anterior": previous_end.strftime("%Y-%m"),
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["serie"]["atual"]) == len(body["serie"]["anterior"]) == size
    assert body["ranking"][0]["alimentador"] == expected.alimentador
    assert body["ranking"][0]["dec"] == pytest.approx(expected.dec, abs=0.5e-6)
    assert body["ranking"][0]["dec_anterior"] == pytest.approx(
        expected_previous_dec, abs=0.5e-6
    )
    assert body["ocorrencias"]["total"] == expected_occurrences["comparado"]
    assert body["ocorrencias"]["total_anterior"] == expected_occurrences["base"]


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_municipio_e_alimentador_conciliam_com_catalogo_e_gold_local() -> None:
    client = TestClient(app)
    options_response = client.get("/api/filters/options")
    assert options_response.status_code == 200
    options = options_response.json()
    city = next(
        row["nome"]
        for row in options["municipios"]
        if any(
            row["nome"] in feeder["municipios"] for feeder in options["alimentadores"]
        )
    )
    expected_codes = {
        feeder["codigo"]
        for feeder in options["alimentadores"]
        if city in feeder["municipios"]
    }

    with get_connection() as connection:
        codes_from_gold = set(
            connection.execute(
                text(
                    "SELECT DISTINCT alimentador FROM dim_unidade_consumidora "
                    "WHERE municipio = :municipio AND alimentador IS NOT NULL"
                ),
                {"municipio": city},
            ).scalars()
        )
        assert expected_codes == codes_from_gold
        last = connection.execute(
            text("SELECT MAX(competencia) FROM dim_competencia")
        ).scalar_one()
        start = _month_at(last.year * 12 + last.month - 12)
        expected_dec = dict(
            connection.execute(
                text(
                    "SELECT alimentador, SUM(dec) FROM agg_continuidade_alimentador "
                    "WHERE competencia BETWEEN :inicio AND :fim "
                    "AND alimentador IN :feeders GROUP BY alimentador"
                ).bindparams(bindparam("feeders", expanding=True)),
                {"inicio": start, "fim": last, "feeders": sorted(expected_codes)},
            ).all()
        )
        expected_count = connection.execute(
            text(
                "SELECT COUNT(*) FROM fact_ocorrencias "
                "WHERE competencia BETWEEN :inicio AND :fim "
                "AND alimentador IN :feeders"
            ).bindparams(bindparam("feeders", expanding=True)),
            {"inicio": start, "fim": last, "feeders": sorted(expected_codes)},
        ).scalar_one()

    response = client.get("/api/network/continuity", params={"municipio": city})
    assert response.status_code == 200, response.text
    body = response.json()
    assert {row["alimentador"] for row in body["ranking"]} == expected_codes
    assert body["serie"]["alimentador"] == body["ranking"][0]["alimentador"]
    assert body["ocorrencias"]["total"] == expected_count
    for row in body["ranking"]:
        assert row["dec"] == pytest.approx(expected_dec[row["alimentador"]], abs=0.5e-6)

    feeder = body["ranking"][0]["alimentador"]
    selected = client.get(
        "/api/network/continuity", params={"municipio": city, "alimentador": feeder}
    )
    assert selected.status_code == 200, selected.text
    selected_body = selected.json()
    assert [row["alimentador"] for row in selected_body["ranking"]] == [feeder]
    assert selected_body["serie"]["alimentador"] == feeder


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_causa_concilia_com_contagem_gold_nas_duas_janelas() -> None:
    with get_connection() as connection:
        first, last = connection.execute(
            text("SELECT MIN(competencia), MAX(competencia) FROM dim_competencia")
        ).one()
        if first is None or last is None or first == last:
            pytest.skip("Calendário Gold local sem duas competências")
        example = connection.execute(
            text(
                "SELECT alimentador, causa FROM fact_ocorrencias "
                "WHERE competencia = :competencia AND causa IS NOT NULL "
                "ORDER BY alimentador, causa LIMIT 1"
            ),
            {"competencia": last},
        ).one_or_none()
        if example is None:
            pytest.skip("Nenhuma ocorrência na última competência Gold")
        expected = {}
        for name, month in (("atual", last), ("anterior", first)):
            expected[name] = connection.execute(
                text(
                    "SELECT COUNT(*) FROM fact_ocorrencias "
                    "WHERE competencia = :competencia "
                    "AND alimentador = :alimentador AND causa = :causa"
                ),
                {
                    "competencia": month,
                    "alimentador": example.alimentador,
                    "causa": example.causa,
                },
            ).scalar_one()

    client = TestClient(app)
    options_response = client.get("/api/filters/options")
    assert options_response.status_code == 200
    options = options_response.json()
    assert example.causa in options["causas"]
    feeder_option = next(
        row for row in options["alimentadores"] if row["codigo"] == example.alimentador
    )
    city = feeder_option["municipios"][0]
    params = {
        "inicio": last.strftime("%Y-%m"),
        "fim": last.strftime("%Y-%m"),
        "inicio_anterior": first.strftime("%Y-%m"),
        "fim_anterior": first.strftime("%Y-%m"),
        "municipio": city,
        "alimentador": example.alimentador,
    }
    baseline = client.get("/api/network/continuity", params=params)
    filtered = client.get(
        "/api/network/continuity", params={**params, "causa": example.causa}
    )

    assert baseline.status_code == filtered.status_code == 200
    before, after = baseline.json(), filtered.json()
    assert after["ranking"] == before["ranking"]
    assert after["serie"] == before["serie"]
    assert after["ocorrencias"]["total"] == expected["atual"]
    assert after["ocorrencias"]["total_anterior"] == expected["anterior"]
    assert after["ocorrencias"]["por_causa"] == [
        {"causa": example.causa, "ocorrencias": expected["atual"]}
    ]


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_gold_mensal_completa_e_equivalente_ao_anual_publicado() -> None:
    columns = ("dec", "fec", "dec_sem_dia_critico", "fec_sem_dia_critico")
    with get_connection() as connection:
        connection.execute(text("SET TRANSACTION READ ONLY"))
        annual = (
            connection.execute(
                text(
                    "SELECT alimentador, ano, total_ucs, dec, fec, "
                    "dec_sem_dia_critico, fec_sem_dia_critico "
                    "FROM agg_continuidade_alimentador_anual WHERE meses = 12 "
                    "ORDER BY ano, alimentador"
                )
            )
            .mappings()
            .all()
        )
        if not annual:
            pytest.skip("Gold local sem ano civil completo")
        monthly = (
            connection.execute(
                text(
                    "SELECT alimentador, ano, COUNT(*) AS meses, "
                    "COUNT(DISTINCT competencia) AS competencias, "
                    "MIN(total_ucs) AS minimo_ucs, MAX(total_ucs) AS maximo_ucs, "
                    "SUM(dec) AS dec, SUM(fec) AS fec, "
                    "SUM(dec_sem_dia_critico) AS dec_sem_dia_critico, "
                    "SUM(fec_sem_dia_critico) AS fec_sem_dia_critico "
                    "FROM agg_continuidade_alimentador "
                    "WHERE ano IN (SELECT ano FROM agg_continuidade_alimentador_anual "
                    "WHERE meses = 12) GROUP BY alimentador, ano"
                )
            )
            .mappings()
            .all()
        )

    by_key = {(row["alimentador"], row["ano"]): row for row in monthly}
    assert len(by_key) == len(monthly) == len(annual)
    for published in annual:
        aggregate = by_key[(published["alimentador"], published["ano"])]
        assert aggregate["meses"] == aggregate["competencias"] == 12
        assert (
            aggregate["minimo_ucs"] == aggregate["maximo_ucs"] == published["total_ucs"]
        )
        assert aggregate["minimo_ucs"] > 0
        for column in columns:
            assert aggregate[column] == pytest.approx(
                published[column], abs=1e-10, rel=1e-10
            )
