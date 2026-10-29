"""Contrato HTTP das opções compartilhadas do snapshot Gold."""

from contextlib import contextmanager, nullcontext

import pytest
from app.controllers import filters as filters_controller
from app.controllers.filters import get_filter_repository
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, ProgrammingError, TimeoutError


class GoldOptionsFake:
    def get_competencias(self) -> list[str]:
        return ["2026-06", "2022-07", "2022-07"]

    def get_municipio_bairro_pairs(self) -> list[tuple[str, str | None]]:
        return [
            ("Recife", "Casa Forte"),
            ("Olinda", "Bairro Novo"),
            ("Recife", "Boa Viagem"),
            ("Recife", "Boa Viagem"),
            ("Recife", None),
        ]

    def get_classes(self) -> list[str]:
        return ["RURAL", "RESIDENCIAL", "RURAL"]

    def get_alimentadores(self) -> list[str]:
        return ["ALM-REC-008", "ALM-CAB-004", "ALM-REC-008"]

    def get_alimentador_municipio_pairs(self) -> list[tuple[str, str]]:
        return [
            ("ALM-REC-008", "Recife"),
            ("ALM-REC-008", "Olinda"),
            ("ALM-REC-008", "Recife"),
            ("ALM-CAB-004", "Cabo de Santo Agostinho"),
        ]

    def get_causas(self) -> list[str]:
        return ["VEGETACAO", "NAO INFORMADA", "NAO IDENTIFICADA", "VEGETACAO"]


def test_catalogo_gold_http_retorna_cinco_grupos_ordenados() -> None:
    app.dependency_overrides[get_filter_repository] = lambda: nullcontext(
        GoldOptionsFake()
    )
    try:
        response = TestClient(app).get("/api/filters/options")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "competencias": ["2022-07", "2026-06"],
        "municipios": [
            {"nome": "Olinda", "bairros": ["Bairro Novo"]},
            {"nome": "Recife", "bairros": ["Boa Viagem", "Casa Forte"]},
        ],
        "classes": ["RESIDENCIAL", "RURAL"],
        "alimentadores": [
            {"codigo": "ALM-CAB-004", "municipios": ["Cabo de Santo Agostinho"]},
            {"codigo": "ALM-REC-008", "municipios": ["Olinda", "Recife"]},
        ],
        "causas": ["NAO IDENTIFICADA", "NAO INFORMADA", "VEGETACAO"],
    }


def test_catalogo_openapi_e_rotas_existentes() -> None:
    client = TestClient(app)
    openapi = client.get("/api/openapi.json").json()
    route = openapi["paths"]["/api/filters/options"]["get"]

    assert route.get("parameters", []) == []
    assert route["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/FilterOptionsResponse"
    }
    response_schema = openapi["components"]["schemas"]["FilterOptionsResponse"]
    assert set(response_schema["properties"]) == {
        "competencias",
        "municipios",
        "classes",
        "alimentadores",
        "causas",
    }
    assert "motivos" not in response_schema["properties"]
    assert client.get("/api/api/filters/options").status_code == 404
    assert client.get("/api/health").status_code == 200
    assert "/api/uc/{uc_id}/360" in openapi["paths"]


def test_falha_de_consulta_nao_vira_catalogo_vazio() -> None:
    class FailingGold(GoldOptionsFake):
        def get_causas(self) -> list[str]:
            raise RuntimeError("falha simulada")

    app.dependency_overrides[get_filter_repository] = lambda: nullcontext(FailingGold())
    try:
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/filters/options"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert (
        response.text
        != '{"competencias":[],"municipios":[],"classes":[],"alimentadores":[],"causas":[]}'
    )


def test_catalogo_vazio_real_mantem_cinco_grupos_e_alimentador_sem_municipio() -> None:
    class EmptyGold(GoldOptionsFake):
        def get_competencias(self) -> list[str]:
            return []

        def get_municipio_bairro_pairs(self) -> list[tuple[str, str | None]]:
            return []

        def get_classes(self) -> list[str]:
            return []

        def get_alimentadores(self) -> list[str]:
            return ["ALM-SEM-MUNICIPIO"]

        def get_alimentador_municipio_pairs(self) -> list[tuple[str, str]]:
            return []

        def get_causas(self) -> list[str]:
            return []

    app.dependency_overrides[get_filter_repository] = lambda: nullcontext(EmptyGold())
    try:
        response = TestClient(app).get("/api/filters/options")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "competencias": [],
        "municipios": [],
        "classes": [],
        "alimentadores": [{"codigo": "ALM-SEM-MUNICIPIO", "municipios": []}],
        "causas": [],
    }


@pytest.mark.parametrize("failure", ["config", "connection", "timeout"])
def test_gold_indisponivel_retorna_503_generico(
    failure: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    if failure == "config":

        @contextmanager
        def missing_config():
            raise RuntimeError("DATABASE_URL não configurada")
            yield

        monkeypatch.setattr(filters_controller, "get_connection", missing_config)
    elif failure == "connection":

        @contextmanager
        def unavailable_connection():
            raise OperationalError("SELECT segredo", {}, Exception("senha privada"))
            yield

        monkeypatch.setattr(
            filters_controller, "get_connection", unavailable_connection
        )
    else:

        class TimedOutGold(GoldOptionsFake):
            def get_causas(self) -> list[str]:
                raise TimeoutError("consulta segredo excedeu tempo")

        app.dependency_overrides[get_filter_repository] = lambda: nullcontext(
            TimedOutGold()
        )

    try:
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/filters/options"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Gold indisponível"}
    assert "segredo" not in response.text
    assert "senha" not in response.text
    assert "DATABASE_URL" not in response.text


@pytest.mark.parametrize("failure", ["schema", "programming"])
def test_falha_inesperada_retorna_500_generico(failure: str) -> None:
    class BrokenGold(GoldOptionsFake):
        def get_causas(self) -> list[str]:
            if failure == "schema":
                raise ProgrammingError(
                    "SELECT segredo", {}, Exception("coluna ausente")
                )
            raise ValueError("segredo de programação")

    app.dependency_overrides[get_filter_repository] = lambda: nullcontext(BrokenGold())
    try:
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/filters/options"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno"}
    assert "segredo" not in response.text
    assert "coluna ausente" not in response.text


def test_contexto_da_conexao_fecha_no_sucesso_e_na_falha() -> None:
    class TrackedContext:
        def __init__(self, repository: GoldOptionsFake) -> None:
            self.repository = repository
            self.closed = False

        def __enter__(self) -> GoldOptionsFake:
            return self.repository

        def __exit__(self, *args: object) -> None:
            self.closed = True

    success = TrackedContext(GoldOptionsFake())

    class FailingGold(GoldOptionsFake):
        def get_causas(self) -> list[str]:
            raise TimeoutError("consulta interrompida")

    failure = TrackedContext(FailingGold())
    contexts = iter((success, failure))
    app.dependency_overrides[get_filter_repository] = lambda: next(contexts)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        assert client.get("/api/filters/options").status_code == 200
        assert client.get("/api/filters/options").status_code == 503
    finally:
        app.dependency_overrides.clear()

    assert success.closed
    assert failure.closed


def test_openapi_documenta_indisponibilidade_gold() -> None:
    operation = (
        TestClient(app)
        .get("/api/openapi.json")
        .json()["paths"]["/api/filters/options"]["get"]
    )
    response = operation["responses"]["503"]
    assert response["content"]["application/json"]["example"] == {
        "detail": "Gold indisponível"
    }
