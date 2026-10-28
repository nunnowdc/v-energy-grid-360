"""Conferência somente leitura do catálogo HTTP contra a Gold local."""

import pytest
from app.core.config import get_settings
from app.core.database import get_connection
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_catalogo_http_corresponde_ao_snapshot_gold() -> None:
    with get_connection() as connection:
        competencias = (
            connection.execute(
                text("SELECT mes_referencia FROM dim_competencia ORDER BY competencia")
            )
            .scalars()
            .all()
        )
        pares_bairro = connection.execute(
            text(
                "SELECT DISTINCT municipio, bairro FROM dim_unidade_consumidora "
                "WHERE municipio IS NOT NULL"
            )
        ).all()
        classes = (
            connection.execute(
                text(
                    "SELECT DISTINCT classe FROM dim_unidade_consumidora "
                    "WHERE classe IS NOT NULL"
                )
            )
            .scalars()
            .all()
        )
        alimentadores = (
            connection.execute(
                text(
                    "SELECT alimentador FROM dim_alimentador "
                    "WHERE alimentador IS NOT NULL"
                )
            )
            .scalars()
            .all()
        )
        pares_alimentador = connection.execute(
            text(
                "SELECT DISTINCT alimentador, municipio FROM dim_unidade_consumidora "
                "WHERE alimentador IS NOT NULL AND municipio IS NOT NULL"
            )
        ).all()
        causas = (
            connection.execute(
                text(
                    "SELECT DISTINCT causa FROM fact_ocorrencias "
                    "WHERE causa IS NOT NULL"
                )
            )
            .scalars()
            .all()
        )

    response = TestClient(app).get("/api/filters/options")
    assert response.status_code == 200
    body = response.json()
    assert body["competencias"] == sorted(set(competencias))
    assert body["classes"] == sorted(set(classes))
    assert body["causas"] == sorted(set(causas))

    expected_bairros: dict[str, set[str]] = {}
    for municipio, bairro in pares_bairro:
        group = expected_bairros.setdefault(municipio, set())
        if bairro is not None:
            group.add(bairro)
    assert body["municipios"] == [
        {"nome": municipio, "bairros": sorted(bairros)}
        for municipio, bairros in sorted(expected_bairros.items())
    ]

    expected_municipios: dict[str, set[str]] = {}
    for alimentador, municipio in pares_alimentador:
        expected_municipios.setdefault(alimentador, set()).add(municipio)
    assert body["alimentadores"] == [
        {"codigo": codigo, "municipios": sorted(expected_municipios.get(codigo, set()))}
        for codigo in sorted(set(alimentadores))
    ]
    multi_municipio = {
        codigo: municipios
        for codigo, municipios in expected_municipios.items()
        if len(municipios) > 1
    }
    if multi_municipio:
        codigo = next(iter(multi_municipio))
        assert next(
            item["municipios"]
            for item in body["alimentadores"]
            if item["codigo"] == codigo
        ) == sorted(multi_municipio[codigo])
