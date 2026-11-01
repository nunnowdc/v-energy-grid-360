"""Contrato HTTP da Receita base sem filtros."""

from contextlib import nullcontext

import pytest
from fastapi.testclient import TestClient

from app.main import app


class RevenueGoldFake:
    def get_calendar(self) -> tuple[str, str]:
        return ("2022-07", "2026-06")

    def get_total(self, periods=None) -> dict[str, object]:
        return {
            "receita_p0": 150.0,
            "receita_p1": 180.0,
            "kwh_p0": 100.0,
            "kwh_p1": 90.0,
            "ucs_p0": 3,
            "ucs_p1": 4,
            "efeito_volume": -10.0,
            "efeito_preco": 40.0,
        }

    def get_by_gd(self, periods=None) -> list[dict[str, object]]:
        return [
            {
                "possui_gd": False,
                "receita_p0": 100.0,
                "receita_p1": 120.0,
                "kwh_p0": 50.0,
                "kwh_p1": 60.0,
                "ucs_p0": 2,
                "ucs_p1": 3,
                "efeito_volume": 10.0,
                "efeito_preco": 10.0,
            },
            {
                "possui_gd": True,
                "receita_p0": 50.0,
                "receita_p1": 60.0,
                "kwh_p0": 50.0,
                "kwh_p1": 30.0,
                "ucs_p0": 1,
                "ucs_p1": 1,
                "efeito_volume": -20.0,
                "efeito_preco": 30.0,
            },
        ]

    def get_by_municipio(self, periods=None) -> list[dict[str, object]]:
        return [
            {"nome": "Recife", **self.get_by_gd()[0]},
            {"nome": "Olinda", **self.get_by_gd()[1]},
        ]


def test_receita_sem_filtros_retorna_cinco_grupos() -> None:
    from app.controllers.metrics import get_revenue_repository

    app.dependency_overrides[get_revenue_repository] = lambda: nullcontext(
        RevenueGoldFake()
    )
    try:
        response = TestClient(app).get("/api/metrics/revenue-variance")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "periodo_p0",
        "periodo_p1",
        "total",
        "por_gd",
        "detalhamento",
    }
    assert body["periodo_p0"] == {"inicio": "2022-07", "fim": "2023-06"}
    assert body["periodo_p1"] == {"inicio": "2025-07", "fim": "2026-06"}
    assert body["total"] == {
        "receita_p0": 150.0,
        "receita_p1": 180.0,
        "kwh_p0": 100.0,
        "kwh_p1": 90.0,
        "ucs_p0": 3,
        "ucs_p1": 4,
        "preco_p0": 1.5,
        "preco_p1": 2.0,
        "efeito_volume": -10.0,
        "efeito_preco": 40.0,
    }
    assert [item["possui_gd"] for item in body["por_gd"]] == [False, True]
    assert all(
        set(group) == set(body["total"]) | {"possui_gd"} for group in body["por_gd"]
    )
    assert all(
        set(row) == set(body["total"]) | {"nome"}
        for row in body["detalhamento"]["linhas"]
    )
    assert body["por_gd"][0]["efeito_preco"] == 10.0
    assert body["por_gd"][1]["efeito_volume"] == -20.0
    assert body["por_gd"][0]["preco_p0"] == 2.0
    assert body["por_gd"][1]["preco_p0"] == 1.0
    assert body["detalhamento"]["nivel"] == "municipio"
    assert [item["nome"] for item in body["detalhamento"]["linhas"]] == [
        "Olinda",
        "Recife",
    ]


def test_receita_preco_nulo_e_grupo_gd_sem_celulas() -> None:
    from app.controllers.metrics import get_revenue_repository

    class SparseGold(RevenueGoldFake):
        def get_total(self, periods=None) -> dict[str, object]:
            return {
                **super().get_total(),
                "kwh_p0": 0.0,
                "kwh_p1": None,
            }

        def get_by_gd(self, periods=None) -> list[dict[str, object]]:
            return [
                {
                    **super().get_by_gd()[0],
                    "kwh_p0": 0.0,
                    "kwh_p1": None,
                }
            ]

        def get_by_municipio(self, periods=None) -> list[dict[str, object]]:
            return [{"nome": "Recife", **self.get_by_gd()[0]}]

    app.dependency_overrides[get_revenue_repository] = lambda: nullcontext(SparseGold())
    try:
        response = TestClient(app).get("/api/metrics/revenue-variance")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["total"]["kwh_p0"] == 0.0
    assert body["total"]["kwh_p1"] is None
    assert body["total"]["preco_p0"] is None
    assert body["total"]["preco_p1"] is None
    assert body["total"]["efeito_preco"] == 40.0
    assert body["total"]["efeito_volume"] == -10.0
    assert body["por_gd"][0]["preco_p0"] is None
    assert body["por_gd"][0]["efeito_preco"] == 10.0
    assert body["por_gd"][0]["efeito_volume"] == 10.0
    assert body["por_gd"][1] == {
        "possui_gd": True,
        **{field: None for field in body["total"]},
    }


def test_receita_preco_nulo_com_consumo_negativo() -> None:
    from app.controllers.metrics import get_revenue_repository

    class NegativeGold(RevenueGoldFake):
        def get_total(self, periods=None) -> dict[str, object]:
            return {**super().get_total(), "kwh_p0": -5.0}

    app.dependency_overrides[get_revenue_repository] = lambda: nullcontext(
        NegativeGold()
    )
    try:
        response = TestClient(app).get("/api/metrics/revenue-variance")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["total"]["preco_p0"] is None


def test_receita_municipios_ordenados_por_perda_e_nome() -> None:
    from app.controllers.metrics import get_revenue_repository

    class RankedGold(RevenueGoldFake):
        def get_by_municipio(self, periods=None) -> list[dict[str, object]]:
            base = super().get_by_gd()[1]
            return [
                {"nome": "Sem consumo", **base, "kwh_p1": None},
                {"nome": "Recife", **base},
                {"nome": "Jaboatão", **base, "kwh_p1": 60.0},
                {"nome": "Olinda", **base},
            ]

    app.dependency_overrides[get_revenue_repository] = lambda: nullcontext(RankedGold())
    try:
        response = TestClient(app).get("/api/metrics/revenue-variance")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert [item["nome"] for item in response.json()["detalhamento"]["linhas"]] == [
        "Olinda",
        "Recife",
        "Jaboatão",
        "Sem consumo",
    ]


def test_receita_nao_ignora_parametro_temporal() -> None:
    response = TestClient(app).get("/api/metrics/revenue-variance?inicio=2022-07")
    assert response.status_code == 422


def test_receita_falha_gold_nao_vira_resposta_vazia_e_libera_contexto() -> None:
    from contextlib import contextmanager

    from sqlalchemy.exc import OperationalError

    from app.controllers.metrics import get_revenue_repository

    released = False

    @contextmanager
    def failing_gold():
        nonlocal released
        try:

            class FailingGold(RevenueGoldFake):
                def get_calendar(self) -> tuple[str, str]:
                    raise OperationalError("SELECT secret", {}, Exception("offline"))

            yield FailingGold()
        finally:
            released = True

    app.dependency_overrides[get_revenue_repository] = lambda: failing_gold()
    try:
        response = TestClient(app).get("/api/metrics/revenue-variance")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Gold indisponível"}
    assert "secret" not in response.text
    assert released


def test_receita_municipio_filtra_total_gd_e_detalha_bairros() -> None:
    from app.controllers.metrics import get_revenue_repository

    class RecifeGold(RevenueGoldFake):
        def has_municipio(self, municipio: str) -> bool:
            return municipio == "Recife"

        def get_total(
            self,
            periods=None,
            municipio: str | None = None,
            bairro: str | None = None,
            classe: str | None = None,
        ) -> dict[str, object]:
            if municipio == "Recife" and bairro is None and classe is None:
                return super().get_by_gd()[0]
            return super().get_total()

        def get_by_gd(
            self,
            periods=None,
            municipio: str | None = None,
            bairro: str | None = None,
            classe: str | None = None,
        ) -> list[dict[str, object]]:
            if municipio == "Recife" and bairro is None and classe is None:
                return [super().get_by_gd()[0]]
            return super().get_by_gd()

        def get_detail(
            self,
            periods,
            level: str,
            municipio: str | None = None,
            bairro: str | None = None,
            classe: str | None = None,
        ) -> list[dict[str, object]]:
            if (
                level == "bairro"
                and municipio == "Recife"
                and bairro is None
                and classe is None
            ):
                return [{"nome": "Boa Viagem", **super().get_by_gd()[0]}]
            return self.get_by_municipio()

    app.dependency_overrides[get_revenue_repository] = lambda: nullcontext(RecifeGold())
    try:
        response = TestClient(app).get(
            "/api/metrics/revenue-variance", params={"municipio": "Recife"}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["total"]["receita_p0"] == 100.0
    assert body["total"]["efeito_preco"] == 10.0
    assert body["por_gd"][0]["receita_p0"] == 100.0
    assert body["por_gd"][1]["receita_p0"] is None
    assert body["detalhamento"]["nivel"] == "bairro"
    assert [row["nome"] for row in body["detalhamento"]["linhas"]] == ["Boa Viagem"]
    assert body["detalhamento"]["linhas"][0]["receita_p0"] == 100.0


class ScopedRevenueGold(RevenueGoldFake):
    """Projeções Gold distintas quando os filtros chegam ao repository."""

    def __init__(
        self,
        expected: tuple[str | None, str | None, str | None],
        level: str,
        detail_name: str,
    ) -> None:
        self.expected = expected
        self.level = level
        self.detail_name = detail_name

    def has_municipio(self, municipio: str) -> bool:
        return municipio in {"Recife", "Olinda"}

    def has_bairro(self, municipio: str, bairro: str) -> bool:
        return (municipio, bairro) in {
            ("Recife", "Boa Viagem"),
            ("Recife", "Casa Forte"),
            ("Olinda", "Bairro Novo"),
        }

    def has_classe(self, classe: str) -> bool:
        return classe in {"RESIDENCIAL", "COMERCIAL"}

    def get_total(
        self,
        periods=None,
        municipio: str | None = None,
        bairro: str | None = None,
        classe: str | None = None,
    ) -> dict[str, object]:
        if (municipio, bairro, classe) == self.expected:
            return super().get_by_gd()[0]
        return super().get_total()

    def get_by_gd(
        self,
        periods=None,
        municipio: str | None = None,
        bairro: str | None = None,
        classe: str | None = None,
    ) -> list[dict[str, object]]:
        if (municipio, bairro, classe) == self.expected:
            return [super().get_by_gd()[0]]
        return super().get_by_gd()

    def get_detail(
        self,
        periods,
        level: str,
        municipio: str | None = None,
        bairro: str | None = None,
        classe: str | None = None,
    ) -> list[dict[str, object]]:
        if (municipio, bairro, classe) == self.expected and level == self.level:
            return [{"nome": self.detail_name, **super().get_by_gd()[0]}]
        return self.get_by_municipio()


def test_receita_municipio_e_bairro_detalham_classes() -> None:
    from app.controllers.metrics import get_revenue_repository

    app.dependency_overrides[get_revenue_repository] = lambda: nullcontext(
        ScopedRevenueGold(("Recife", "Boa Viagem", None), "classe", "RESIDENCIAL")
    )
    try:
        response = TestClient(app).get(
            "/api/metrics/revenue-variance",
            params={"municipio": "Recife", "bairro": "Boa Viagem"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["total"]["receita_p0"] == 100.0
    assert body["por_gd"][0]["receita_p0"] == 100.0
    assert body["por_gd"][1]["receita_p0"] is None
    assert body["detalhamento"]["nivel"] == "classe"
    assert [item["nome"] for item in body["detalhamento"]["linhas"]] == ["RESIDENCIAL"]
    assert body["detalhamento"]["linhas"][0]["receita_p0"] == 100.0


def test_receita_classe_isolada_mantem_detalhamento_municipal() -> None:
    from app.controllers.metrics import get_revenue_repository

    app.dependency_overrides[get_revenue_repository] = lambda: nullcontext(
        ScopedRevenueGold((None, None, "COMERCIAL"), "municipio", "Recife")
    )
    try:
        response = TestClient(app).get(
            "/api/metrics/revenue-variance", params={"classe": "COMERCIAL"}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["total"]["receita_p0"] == 100.0
    assert body["por_gd"][0]["receita_p0"] == 100.0
    assert body["por_gd"][1]["receita_p0"] is None
    assert body["detalhamento"]["nivel"] == "municipio"
    assert [item["nome"] for item in body["detalhamento"]["linhas"]] == ["Recife"]


def test_receita_municipio_bairro_e_classe_retorna_so_classe_escolhida() -> None:
    from app.controllers.metrics import get_revenue_repository

    app.dependency_overrides[get_revenue_repository] = lambda: nullcontext(
        ScopedRevenueGold(
            ("Recife", "Boa Viagem", "RESIDENCIAL"), "classe", "RESIDENCIAL"
        )
    )
    try:
        response = TestClient(app).get(
            "/api/metrics/revenue-variance",
            params={
                "municipio": "Recife",
                "bairro": "Boa Viagem",
                "classe": "RESIDENCIAL",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "periodo_p0",
        "periodo_p1",
        "total",
        "por_gd",
        "detalhamento",
    }
    assert body["periodo_p0"] == {"inicio": "2022-07", "fim": "2023-06"}
    assert body["total"]["receita_p0"] == 100.0
    assert body["por_gd"][0]["receita_p0"] == 100.0
    assert body["detalhamento"]["nivel"] == "classe"
    assert [row["nome"] for row in body["detalhamento"]["linhas"]] == ["RESIDENCIAL"]
    assert body["detalhamento"]["linhas"][0]["receita_p0"] == 100.0


def test_receita_municipio_e_classe_detalham_bairros() -> None:
    from app.controllers.metrics import get_revenue_repository

    app.dependency_overrides[get_revenue_repository] = lambda: nullcontext(
        ScopedRevenueGold(("Recife", None, "COMERCIAL"), "bairro", "Casa Forte")
    )
    try:
        response = TestClient(app).get(
            "/api/metrics/revenue-variance",
            params={"municipio": "Recife", "classe": "COMERCIAL"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["total"]["receita_p0"] == 100.0
    assert body["por_gd"][1]["receita_p0"] is None
    assert body["detalhamento"]["nivel"] == "bairro"
    assert [row["nome"] for row in body["detalhamento"]["linhas"]] == ["Casa Forte"]


def test_receita_parametros_vazios_equivalem_a_omissao() -> None:
    from app.controllers.metrics import get_revenue_repository

    app.dependency_overrides[get_revenue_repository] = lambda: nullcontext(
        RevenueGoldFake()
    )
    try:
        client = TestClient(app)
        without_filters = client.get("/api/metrics/revenue-variance")
        empty_filters = client.get(
            "/api/metrics/revenue-variance?municipio=&bairro=&classe="
        )
    finally:
        app.dependency_overrides.clear()

    assert without_filters.status_code == empty_filters.status_code == 200
    assert without_filters.json() == empty_filters.json()


@pytest.mark.parametrize(
    "query",
    [
        "?municipio=Desconhecido",
        "?classe=DESCONHECIDA",
        "?bairro=Boa%20Viagem",
        "?municipio=Recife&bairro=Bairro%20Novo",
        "?municipio=Recife&municipio=Olinda",
        "?bairro=Boa%20Viagem&bairro=Casa%20Forte",
        "?classe=RESIDENCIAL&classe=COMERCIAL",
        "?foo=1",
        "?fim=2026-06",
        "?municipio=&bairro=Boa%20Viagem",
    ],
)
def test_receita_rejeita_filtros_invalidos(query: str) -> None:
    from app.controllers.metrics import get_revenue_repository

    app.dependency_overrides[get_revenue_repository] = lambda: nullcontext(
        ScopedRevenueGold((None, None, None), "municipio", "Recife")
    )
    try:
        response = TestClient(app).get("/api/metrics/revenue-variance" + query)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert set(response.json()) == {"detail"}
    assert "SELECT" not in response.text


def test_receita_recorte_valido_sem_celulas_retorna_nulos() -> None:
    from app.controllers.metrics import get_revenue_repository

    class EmptySliceGold(ScopedRevenueGold):
        def get_total(
            self,
            periods=None,
            municipio: str | None = None,
            bairro: str | None = None,
            classe: str | None = None,
        ) -> dict[str, object]:
            return {field: None for field in RevenueGoldFake.get_total(self)}

        def get_by_gd(
            self,
            periods=None,
            municipio: str | None = None,
            bairro: str | None = None,
            classe: str | None = None,
        ) -> list[dict[str, object]]:
            return []

        def get_detail(
            self,
            periods,
            level: str,
            municipio: str | None = None,
            bairro: str | None = None,
            classe: str | None = None,
        ) -> list[dict[str, object]]:
            return []

    app.dependency_overrides[get_revenue_repository] = lambda: nullcontext(
        EmptySliceGold(("Recife", "Casa Forte", "COMERCIAL"), "classe", "COMERCIAL")
    )
    try:
        response = TestClient(app).get(
            "/api/metrics/revenue-variance",
            params={
                "municipio": "Recife",
                "bairro": "Casa Forte",
                "classe": "COMERCIAL",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["periodo_p0"] == {"inicio": "2022-07", "fim": "2023-06"}
    assert all(value is None for value in body["total"].values())
    assert [row["possui_gd"] for row in body["por_gd"]] == [False, True]
    assert all(
        value is None
        for row in body["por_gd"]
        for field, value in row.items()
        if field != "possui_gd"
    )
    assert body["detalhamento"] == {"nivel": "classe", "linhas": []}


def test_receita_detalhamento_filtrado_ordena_perda_empate_e_nulos() -> None:
    from app.controllers.metrics import get_revenue_repository

    class RankedFilteredGold(ScopedRevenueGold):
        def get_detail(
            self,
            periods,
            level: str,
            municipio: str | None = None,
            bairro: str | None = None,
            classe: str | None = None,
        ) -> list[dict[str, object]]:
            base = RevenueGoldFake.get_by_gd(self)[0]
            return [
                {"nome": "Sem consumo", **base, "kwh_p1": None},
                {"nome": "Boa Viagem", **base, "kwh_p1": 40.0},
                {"nome": "Casa Forte", **base, "kwh_p1": 40.0},
                {"nome": "Afogados", **base, "kwh_p1": 20.0},
            ]

    app.dependency_overrides[get_revenue_repository] = lambda: nullcontext(
        RankedFilteredGold(("Recife", None, None), "bairro", "Boa Viagem")
    )
    try:
        response = TestClient(app).get(
            "/api/metrics/revenue-variance", params={"municipio": "Recife"}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert [row["nome"] for row in response.json()["detalhamento"]["linhas"]] == [
        "Afogados",
        "Boa Viagem",
        "Casa Forte",
        "Sem consumo",
    ]


def test_receita_openapi_documenta_os_filtros_e_os_periodos() -> None:
    operation = (
        TestClient(app)
        .get("/api/openapi.json")
        .json()["paths"]["/api/metrics/revenue-variance"]["get"]
    )
    assert {parameter["name"] for parameter in operation["parameters"]} == {
        "municipio",
        "bairro",
        "classe",
        "inicio_p0",
        "fim_p0",
        "inicio_p1",
        "fim_p1",
        "vgrid360_access_token",
    }


def test_receita_openapi_documenta_duas_causas_de_503() -> None:
    operation = (
        TestClient(app)
        .get("/api/openapi.json")
        .json()["paths"]["/api/metrics/revenue-variance"]["get"]
    )
    assert set(operation["responses"]) >= {"200", "422", "500", "503"}
    response = operation["responses"]["503"]
    examples = response["content"]["application/json"]["examples"]
    assert {item["value"]["detail"] for item in examples.values()} == {
        "Gold indisponível",
        "Dados Gold indisponíveis para comparação de receita",
    }
    assert operation["responses"]["500"]["content"]["application/json"]["example"] == {
        "detail": "Erro interno"
    }
    assert (
        "/api/api/metrics/revenue-variance"
        not in TestClient(app).get("/api/openapi.json").json()["paths"]
    )


@pytest.mark.parametrize(
    "calendar",
    [
        (None, None),
        (None, "2026-06"),
        ("2022-07", None),
        ("2022-07", "2024-05"),
        ("2022-13", "2026-06"),
        (202207, 202606),
    ],
)
def test_receita_metadados_gold_invalidos_retorna_503_antes_do_recorte(
    calendar: tuple[object, object],
) -> None:
    from app.controllers.metrics import get_revenue_repository

    class InvalidMetadataGold(ScopedRevenueGold):
        def get_calendar(self) -> tuple[object, object]:
            return calendar

        def has_municipio(self, municipio: str) -> bool:
            pytest.fail("catálogo não deve ser consultado antes dos metadados")

    app.dependency_overrides[get_revenue_repository] = lambda: nullcontext(
        InvalidMetadataGold(("Recife", None, None), "bairro", "Boa Viagem")
    )
    try:
        response = TestClient(app).get(
            "/api/metrics/revenue-variance", params={"municipio": "Recife"}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Dados Gold indisponíveis para comparação de receita"
    }


@pytest.mark.parametrize("failure", ["config", "connection", "timeout"])
def test_receita_indisponibilidade_gold_retorna_503_sem_vazamento(
    failure: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from contextlib import contextmanager

    from sqlalchemy.exc import OperationalError, TimeoutError

    from app.controllers import metrics as metrics_controller
    from app.controllers.metrics import get_revenue_repository

    if failure in {"config", "connection"}:

        @contextmanager
        def broken_connection():
            if failure == "config":
                raise RuntimeError("DATABASE_URL não configurada")
            raise OperationalError("SELECT segredo", {}, Exception("senha privada"))
            yield

        monkeypatch.setattr(metrics_controller, "get_connection", broken_connection)
    else:

        class TimedOutGold(RevenueGoldFake):
            def get_total(self, periods=None) -> dict[str, object]:
                raise TimeoutError("SELECT segredo excedeu o tempo")

        app.dependency_overrides[get_revenue_repository] = lambda: nullcontext(
            TimedOutGold()
        )

    try:
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/metrics/revenue-variance"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Gold indisponível"}
    assert "segredo" not in response.text
    assert "senha" not in response.text
    assert "DATABASE_URL" not in response.text


@pytest.mark.parametrize("failure", ["schema", "programming", "runtime"])
def test_receita_falha_inesperada_retorna_500_sem_vazamento(failure: str) -> None:
    from sqlalchemy.exc import ProgrammingError

    from app.controllers.metrics import get_revenue_repository

    class BrokenGold(RevenueGoldFake):
        def get_total(self, periods=None) -> dict[str, object]:
            if failure == "schema":
                raise ProgrammingError(
                    "SELECT segredo", {}, Exception("coluna ausente")
                )
            if failure == "runtime":
                raise RuntimeError("segredo de programação")
            raise ValueError("segredo de programação")

    app.dependency_overrides[get_revenue_repository] = lambda: nullcontext(BrokenGold())
    try:
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/metrics/revenue-variance"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno"}
    assert "segredo" not in response.text
    assert "coluna ausente" not in response.text


def test_receita_contexto_de_conexao_fecha_apos_sucesso_e_falha() -> None:
    from app.controllers.metrics import get_revenue_repository

    class TrackedContext:
        def __init__(self, repository: RevenueGoldFake) -> None:
            self.repository = repository
            self.closed = False

        def __enter__(self) -> RevenueGoldFake:
            return self.repository

        def __exit__(self, *args: object) -> None:
            self.closed = True

    class FailingGold(RevenueGoldFake):
        def get_total(self, periods=None) -> dict[str, object]:
            raise ValueError("falha de composição")

    success = TrackedContext(RevenueGoldFake())
    failure = TrackedContext(FailingGold())
    contexts = iter((success, failure))
    app.dependency_overrides[get_revenue_repository] = lambda: next(contexts)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        assert client.get("/api/metrics/revenue-variance").status_code == 200
        assert client.get("/api/metrics/revenue-variance").status_code == 500
    finally:
        app.dependency_overrides.clear()

    assert success.closed
    assert failure.closed


def test_receita_resposta_gold_incompativel_com_schema_retorna_500_generico() -> None:
    from app.controllers.metrics import get_revenue_repository

    class InvalidMeasureGold(RevenueGoldFake):
        def get_total(self, periods=None) -> dict[str, object]:
            return {**super().get_total(), "receita_p0": "valor-inválido"}

    app.dependency_overrides[get_revenue_repository] = lambda: nullcontext(
        InvalidMeasureGold()
    )
    try:
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/metrics/revenue-variance"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno"}
    assert "valor-inválido" not in response.text


class PeriodsRevenueGold(RevenueGoldFake):
    """Guarda os períodos que chegam a cada consulta."""

    def __init__(self) -> None:
        self.received: list[object] = []

    def get_total(self, periods=None) -> dict[str, object]:
        self.received.append(periods)
        return super().get_total()

    def get_by_gd(self, periods=None) -> list[dict[str, object]]:
        self.received.append(periods)
        return super().get_by_gd()

    def get_by_municipio(self, periods=None) -> list[dict[str, object]]:
        self.received.append(periods)
        # Monta pelas linhas do falso base, sem passar pelo get_by_gd que registra
        groups = RevenueGoldFake.get_by_gd(self)
        return [{"nome": "Recife", **groups[0]}, {"nome": "Olinda", **groups[1]}]


def _periods_response(params: dict[str, str]) -> tuple[object, PeriodsRevenueGold]:
    from app.controllers.metrics import get_revenue_repository

    gold = PeriodsRevenueGold()
    app.dependency_overrides[get_revenue_repository] = lambda: nullcontext(gold)
    try:
        response = TestClient(app).get("/api/metrics/revenue-variance", params=params)
    finally:
        app.dependency_overrides.clear()
    return response, gold


def test_receita_sem_periodos_compara_primeiro_ano_com_ultimos_12_meses() -> None:
    from app.repositories.revenue import RevenuePeriods

    response, gold = _periods_response({})

    assert response.status_code == 200
    body = response.json()
    assert body["periodo_p0"] == {"inicio": "2022-07", "fim": "2023-06"}
    assert body["periodo_p1"] == {"inicio": "2025-07", "fim": "2026-06"}
    assert (
        gold.received
        == [RevenuePeriods("2022-07", "2023-06", "2025-07", "2026-06")] * 3
    )


def test_receita_periodos_escolhidos_chegam_as_consultas() -> None:
    from app.repositories.revenue import RevenuePeriods

    response, gold = _periods_response(
        _quatro("2023-01", "2023-03", "2025-07", "2025-09")
    )

    assert response.status_code == 200
    body = response.json()
    assert body["periodo_p0"] == {"inicio": "2023-01", "fim": "2023-03"}
    assert body["periodo_p1"] == {"inicio": "2025-07", "fim": "2025-09"}
    assert (
        gold.received
        == [RevenuePeriods("2023-01", "2023-03", "2025-07", "2025-09")] * 3
    )


def test_receita_periodos_vazios_equivalem_a_omissao() -> None:
    without_periods, _ = _periods_response({})
    empty_periods, _ = _periods_response(_quatro("", "", "", ""))

    assert empty_periods.status_code == 200
    assert empty_periods.json() == without_periods.json()


def _quatro(inicio_p0: str, fim_p0: str, inicio_p1: str, fim_p1: str) -> dict[str, str]:
    return {
        "inicio_p0": inicio_p0,
        "fim_p0": fim_p0,
        "inicio_p1": inicio_p1,
        "fim_p1": fim_p1,
    }


@pytest.mark.parametrize(
    "params",
    [
        # Faltando algum dos quatro meses
        {"inicio_p0": "2022-07", "fim_p0": "2023-06"},
        {"inicio_p0": "2022-07", "fim_p0": "2023-06", "inicio_p1": "2025-07"},
        # Mês mal escrito
        _quatro("2022-7", "2023-06", "2025-07", "2026-06"),
        _quatro("2022-07", "2023-06", "2025-07", "2026-13"),
        # Tamanhos diferentes, base invertido ou maior que 24 meses
        _quatro("2022-07", "2023-06", "2025-07", "2026-05"),
        _quatro("2023-06", "2022-07", "2025-07", "2026-06"),
        _quatro("2022-07", "2024-07", "2024-08", "2026-08"),
        # Antes do primeiro mês ou depois do último mês da base
        _quatro("2022-06", "2023-05", "2025-07", "2026-06"),
        _quatro("2022-07", "2023-06", "2025-08", "2026-07"),
        # Comparado antes do base ou sobreposto a ele
        _quatro("2025-07", "2026-06", "2022-07", "2023-06"),
        _quatro("2022-07", "2023-06", "2023-06", "2024-05"),
    ],
)
def test_receita_rejeita_periodos_invalidos(params: dict[str, str]) -> None:
    response, gold = _periods_response(params)

    assert response.status_code == 422
    assert set(response.json()) == {"detail"}
    assert gold.received == []


def test_receita_rejeita_periodo_repetido() -> None:
    response = TestClient(app).get(
        "/api/metrics/revenue-variance?inicio_p0=2022-07&inicio_p0=2023-07"
        "&fim_p0=2023-06&inicio_p1=2025-07&fim_p1=2026-06"
    )
    assert response.status_code == 422
