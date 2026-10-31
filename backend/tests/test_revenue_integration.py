"""Comparação HTTP da Receita com a agregação Gold local, somente leitura."""

import pytest
from app.core.config import get_settings
from app.core.database import get_connection
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_receita_sem_filtros_corresponde_a_gold_local() -> None:
    response = TestClient(app).get("/api/metrics/revenue-variance")
    assert response.status_code == 200
    body = response.json()

    with get_connection() as connection:
        periods = connection.execute(
            text("SELECT DISTINCT periodo_p0, periodo_p1 FROM agg_receita_preco_volume")
        ).all()
        totals = (
            connection.execute(
                text(
                    "SELECT SUM(receita_p0) AS receita_p0, "
                    "SUM(receita_p1) AS receita_p1, "
                    "SUM(kwh_p0) AS kwh_p0, SUM(kwh_p1) AS kwh_p1, "
                    "SUM(ucs_p0) AS ucs_p0, SUM(ucs_p1) AS ucs_p1, "
                    "SUM(efeito_volume) AS efeito_volume, "
                    "SUM(efeito_preco) AS efeito_preco "
                    "FROM agg_receita_preco_volume"
                )
            )
            .mappings()
            .one()
        )
        gd_counts = connection.execute(
            text(
                "SELECT possui_gd, COUNT(*) AS cells "
                "FROM agg_receita_preco_volume GROUP BY possui_gd"
            )
        ).all()
        municipality_order = (
            connection.execute(
                text(
                    "SELECT municipio FROM agg_receita_preco_volume "
                    "GROUP BY municipio "
                    "ORDER BY SUM(kwh_p1) - SUM(kwh_p0) ASC NULLS LAST, municipio"
                )
            )
            .scalars()
            .all()
        )

    assert periods == [("2022-07 a 2023-06", "2025-07 a 2026-06")]
    assert body["periodo_p0"] == {"inicio": "2022-07", "fim": "2023-06"}
    assert body["periodo_p1"] == {"inicio": "2025-07", "fim": "2026-06"}
    for field in (
        "receita_p0",
        "receita_p1",
        "kwh_p0",
        "kwh_p1",
        "efeito_volume",
        "efeito_preco",
    ):
        assert body["total"][field] == pytest.approx(totals[field])
    assert body["total"]["ucs_p0"] == totals["ucs_p0"]
    assert body["total"]["ucs_p1"] == totals["ucs_p1"]
    assert body["total"]["preco_p0"] == pytest.approx(
        totals["receita_p0"] / totals["kwh_p0"]
    )
    assert body["total"]["preco_p1"] == pytest.approx(
        totals["receita_p1"] / totals["kwh_p1"]
    )
    assert [group["possui_gd"] for group in body["por_gd"]] == [False, True]
    assert {status for status, _ in gd_counts} == {False, True}
    for field in (
        "receita_p0",
        "receita_p1",
        "kwh_p0",
        "kwh_p1",
        "efeito_volume",
        "efeito_preco",
    ):
        assert sum(group[field] for group in body["por_gd"]) == pytest.approx(
            totals[field]
        )
        assert sum(
            row[field] for row in body["detalhamento"]["linhas"]
        ) == pytest.approx(totals[field])
    for field in ("ucs_p0", "ucs_p1"):
        assert sum(group[field] for group in body["por_gd"]) == totals[field]
        assert (
            sum(row[field] for row in body["detalhamento"]["linhas"]) == totals[field]
        )
    assert [row["nome"] for row in body["detalhamento"]["linhas"]] == (
        municipality_order
    )
    assert body["total"]["receita_p1"] - body["total"]["receita_p0"] == (
        pytest.approx(
            body["total"]["efeito_volume"] + body["total"]["efeito_preco"],
            abs=0.01,
        )
    )


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_receita_recortes_correspondem_as_celulas_gold() -> None:
    with get_connection() as connection:
        sample = (
            connection.execute(
                text(
                    "SELECT municipio, bairro, classe "
                    "FROM agg_receita_preco_volume "
                    "WHERE municipio IS NOT NULL AND bairro IS NOT NULL "
                    "AND classe IS NOT NULL ORDER BY municipio, bairro, classe LIMIT 1"
                )
            )
            .mappings()
            .one()
        )

    cases = [
        ({"municipio": sample["municipio"]}, "bairro"),
        (
            {"municipio": sample["municipio"], "bairro": sample["bairro"]},
            "classe",
        ),
        ({"classe": sample["classe"]}, "municipio"),
        (
            {
                "municipio": sample["municipio"],
                "bairro": sample["bairro"],
                "classe": sample["classe"],
            },
            "classe",
        ),
    ]
    additive = (
        "receita_p0",
        "receita_p1",
        "kwh_p0",
        "kwh_p1",
        "ucs_p0",
        "ucs_p1",
        "efeito_volume",
        "efeito_preco",
    )
    sums = ", ".join(f"SUM({field}) AS {field}" for field in additive)
    client = TestClient(app)
    for filters, level in cases:
        response = client.get("/api/metrics/revenue-variance", params=filters)
        assert response.status_code == 200
        body = response.json()
        predicates = " AND ".join(f"{field} = :{field}" for field in filters)
        with get_connection() as connection:
            total = (
                connection.execute(
                    text(
                        f"SELECT {sums} FROM agg_receita_preco_volume WHERE {predicates}"
                    ),
                    filters,
                )
                .mappings()
                .one()
            )
            gd = {
                row["possui_gd"]: row
                for row in connection.execute(
                    text(
                        f"SELECT possui_gd, {sums} FROM agg_receita_preco_volume "
                        f"WHERE {predicates} GROUP BY possui_gd"
                    ),
                    filters,
                ).mappings()
            }
            details = list(
                connection.execute(
                    text(
                        f"SELECT {level} AS nome, {sums} "
                        f"FROM agg_receita_preco_volume WHERE {predicates} "
                        f"GROUP BY {level} ORDER BY "
                        "SUM(kwh_p1) - SUM(kwh_p0) ASC NULLS LAST, nome"
                    ),
                    filters,
                ).mappings()
            )
        assert body["detalhamento"]["nivel"] == level
        assert [row["nome"] for row in body["detalhamento"]["linhas"]] == [
            row["nome"] for row in details
        ]
        assert [row["possui_gd"] for row in body["por_gd"]] == [False, True]
        for field in additive:
            assert body["total"][field] == pytest.approx(total[field])
            for group in body["por_gd"]:
                expected = gd.get(group["possui_gd"])
                if expected is None:
                    assert group[field] is None
                else:
                    assert group[field] == pytest.approx(expected[field])
            for actual, expected in zip(
                body["detalhamento"]["linhas"], details, strict=True
            ):
                assert actual[field] == pytest.approx(expected[field])


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_receita_recorte_gold_com_um_grupo_gd_preserva_outro_nulo() -> None:
    with get_connection() as connection:
        sample = (
            connection.execute(
                text(
                    "SELECT municipio, bairro, classe, MIN(possui_gd::int) AS status "
                    "FROM agg_receita_preco_volume "
                    "GROUP BY municipio, bairro, classe "
                    "HAVING COUNT(DISTINCT possui_gd) = 1 "
                    "ORDER BY municipio, bairro, classe LIMIT 1"
                )
            )
            .mappings()
            .one()
        )
    filters = {key: sample[key] for key in ("municipio", "bairro", "classe")}
    response = TestClient(app).get("/api/metrics/revenue-variance", params=filters)
    assert response.status_code == 200
    body = response.json()
    assert body["detalhamento"]["nivel"] == "classe"
    assert [row["nome"] for row in body["detalhamento"]["linhas"]] == [sample["classe"]]
    present = bool(sample["status"])
    missing_group = next(
        group for group in body["por_gd"] if group["possui_gd"] is not present
    )
    assert all(
        value is None for field, value in missing_group.items() if field != "possui_gd"
    )
    present_group = next(
        group for group in body["por_gd"] if group["possui_gd"] is present
    )
    for field in (
        "receita_p0",
        "receita_p1",
        "kwh_p0",
        "kwh_p1",
        "ucs_p0",
        "ucs_p1",
        "efeito_volume",
        "efeito_preco",
    ):
        assert present_group[field] == pytest.approx(body["total"][field])


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_receita_snapshot_gold_unico_e_efeitos_conciliados_sem_ajuste() -> None:
    with get_connection() as connection:
        integrity = (
            connection.execute(
                text(
                    "SELECT COUNT(*) AS celulas, "
                    "COUNT(DISTINCT (municipio, bairro, classe, possui_gd)) "
                    "AS chaves, "
                    "COUNT(DISTINCT (periodo_p0, periodo_p1)) AS pares_periodo "
                    "FROM agg_receita_preco_volume"
                )
            )
            .mappings()
            .one()
        )
    assert integrity["celulas"] > 0
    assert integrity["chaves"] == integrity["celulas"]
    assert integrity["pares_periodo"] == 1

    response = TestClient(app).get("/api/metrics/revenue-variance")
    assert response.status_code == 200
    body = response.json()
    segments = [
        body["total"],
        *body["por_gd"],
        *body["detalhamento"]["linhas"],
    ]
    for segment in segments:
        if all(
            segment[field] is not None
            for field in ("receita_p0", "receita_p1", "efeito_volume", "efeito_preco")
        ):
            assert segment["receita_p1"] - segment["receita_p0"] == pytest.approx(
                segment["efeito_volume"] + segment["efeito_preco"],
                abs=0.01,
                rel=0,
            )
        for period in ("p0", "p1"):
            revenue = segment[f"receita_{period}"]
            consumption = segment[f"kwh_{period}"]
            price = segment[f"preco_{period}"]
            if consumption is None or consumption <= 0 or revenue is None:
                assert price is None
            else:
                assert price == pytest.approx(revenue / consumption)


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_receita_outros_periodos_correspondem_a_serie_mensal_gold() -> None:
    response = TestClient(app).get(
        "/api/metrics/revenue-variance",
        params={
            "municipio": "Recife",
            "inicio_p0": "2023-07",
            "fim_p0": "2024-06",
            "inicio_p1": "2024-07",
            "fim_p1": "2025-06",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["periodo_p0"] == {"inicio": "2023-07", "fim": "2024-06"}
    assert body["periodo_p1"] == {"inicio": "2024-07", "fim": "2025-06"}

    with get_connection() as connection:
        expected = (
            connection.execute(
                text(
                    "SELECT "
                    "SUM(receita_faturada) FILTER (WHERE mes_referencia "
                    "BETWEEN '2023-07' AND '2024-06') AS receita_p0, "
                    "SUM(receita_faturada) FILTER (WHERE mes_referencia "
                    "BETWEEN '2024-07' AND '2025-06') AS receita_p1, "
                    "SUM(consumo_kwh) FILTER (WHERE mes_referencia "
                    "BETWEEN '2023-07' AND '2024-06') AS kwh_p0, "
                    "SUM(consumo_kwh) FILTER (WHERE mes_referencia "
                    "BETWEEN '2024-07' AND '2025-06') AS kwh_p1, "
                    "SUM(ucs_faturadas) FILTER (WHERE mes_referencia = '2024-06') "
                    "AS ucs_p0, "
                    "SUM(ucs_faturadas) FILTER (WHERE mes_referencia = '2025-06') "
                    "AS ucs_p1 "
                    "FROM agg_receita_mensal WHERE municipio = 'Recife'"
                )
            )
            .mappings()
            .one()
        )

    total = body["total"]
    for field, value in expected.items():
        assert total[field] == pytest.approx(float(value), abs=0.01, rel=0)
    assert total["receita_p1"] - total["receita_p0"] == pytest.approx(
        total["efeito_volume"] + total["efeito_preco"], abs=0.01, rel=0
    )
    # Com e sem GD, e os bairros do detalhe, somam o total do recorte
    for parts in (body["por_gd"], body["detalhamento"]["linhas"]):
        for field in ("receita_p0", "receita_p1", "efeito_volume", "efeito_preco"):
            assert sum(part[field] or 0 for part in parts) == pytest.approx(
                total[field], abs=0.01, rel=0
            )


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_receita_trimestres_de_anos_diferentes_conciliam_efeitos() -> None:
    response = TestClient(app).get(
        "/api/metrics/revenue-variance",
        params={
            "inicio_p0": "2023-01",
            "fim_p0": "2023-03",
            "inicio_p1": "2026-01",
            "fim_p1": "2026-03",
        },
    )
    assert response.status_code == 200
    body = response.json()

    with get_connection() as connection:
        expected = (
            connection.execute(
                text(
                    "SELECT "
                    "SUM(receita_faturada) FILTER (WHERE mes_referencia "
                    "BETWEEN '2023-01' AND '2023-03') AS receita_p0, "
                    "SUM(receita_faturada) FILTER (WHERE mes_referencia "
                    "BETWEEN '2026-01' AND '2026-03') AS receita_p1 "
                    "FROM agg_receita_mensal"
                )
            )
            .mappings()
            .one()
        )

    total = body["total"]
    assert total["receita_p0"] == pytest.approx(expected["receita_p0"], abs=0.01)
    assert total["receita_p1"] == pytest.approx(expected["receita_p1"], abs=0.01)
    assert total["receita_p1"] - total["receita_p0"] == pytest.approx(
        total["efeito_volume"] + total["efeito_preco"], abs=0.01, rel=0
    )
