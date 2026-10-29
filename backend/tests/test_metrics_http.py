"""Contrato HTTP inicial dos indicadores consolidados da Gold."""

from contextlib import contextmanager, nullcontext
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.controllers import metrics as metrics_controller
from app.controllers.metrics import get_metrics_repository
from app.main import app


class MetricsGoldFake:
    def get_calendar(self) -> list[tuple[date, str]]:
        return [
            (date(year, month, 1), f"{year:04d}-{month:02d}")
            for year in (2024, 2025)
            for month in range(1, 13)
        ]

    def get_monthly_metrics(self, inicio: date, fim: date) -> list[dict[str, object]]:
        rows = [
            {
                "competencia": date(2024, 12, 1),
                "receita_faturada": 20.0,
                "consumo_kwh": 10.0,
                "ucs_faturadas": 5,
                "faturas": 6,
                "faturas_atrasadas": 1,
            },
            {
                "competencia": date(2025, 9, 1),
                "receita_faturada": 50.0,
                "consumo_kwh": 5.0,
                "ucs_faturadas": 4,
                "faturas": 5,
                "faturas_atrasadas": 2,
            },
            {
                "competencia": date(2025, 10, 1),
                "receita_faturada": 0.0,
                "consumo_kwh": 0.0,
                "ucs_faturadas": 0,
                "faturas": 0,
                "faturas_atrasadas": 0,
            },
            {
                "competencia": date(2025, 11, 1),
                "receita_faturada": 70.0,
                "consumo_kwh": 20.0,
                "ucs_faturadas": 3,
                "faturas": 4,
                "faturas_atrasadas": 2,
            },
            {
                "competencia": date(2025, 12, 1),
                "receita_faturada": 30.0,
                "consumo_kwh": 10.0,
                "ucs_faturadas": 2,
                "faturas": 3,
                "faturas_atrasadas": 1,
            },
        ]
        return [row for row in rows if inicio <= row["competencia"] <= fim]

    def get_class_revenue(self, inicio: date, fim: date) -> list[dict[str, object]]:
        rows = [
            {
                "competencia": date(2024, 12, 1),
                "classe": "RESIDENCIAL",
                "receita_faturada": 20.0,
            },
            {
                "competencia": date(2025, 9, 1),
                "classe": "RESIDENCIAL",
                "receita_faturada": 50.0,
            },
            {
                "competencia": date(2025, 10, 1),
                "classe": "RESIDENCIAL",
                "receita_faturada": 0.0,
            },
            {
                "competencia": date(2025, 11, 1),
                "classe": "RESIDENCIAL",
                "receita_faturada": 40.0,
            },
            {
                "competencia": date(2025, 11, 1),
                "classe": "COMERCIAL",
                "receita_faturada": 30.0,
            },
            {
                "competencia": date(2025, 12, 1),
                "classe": "RESIDENCIAL",
                "receita_faturada": 30.0,
            },
        ]
        return [row for row in rows if inicio <= row["competencia"] <= fim]

    def get_classes(self) -> list[str]:
        return ["RESIDENCIAL", "COMERCIAL", "INDUSTRIAL", "RURAL", "PODER_PUBLICO"]


def get_response(
    params: dict[str, str] | None = None, gold: MetricsGoldFake | None = None
):
    app.dependency_overrides[get_metrics_repository] = lambda: nullcontext(
        gold or MetricsGoldFake()
    )
    try:
        return TestClient(app).get("/api/metrics/general", params=params)
    finally:
        app.dependency_overrides.clear()


def test_indicadores_sem_filtros_retorna_quatro_grupos() -> None:
    response = get_response()

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"atual", "anterior", "mensal", "por_classe"}
    assert set(body["atual"]) == {
        "inicio",
        "fim",
        "receita_faturada",
        "consumo_kwh",
        "preco_medio_kwh",
        "ucs_faturadas",
        "faturas",
        "faturas_atrasadas",
    }
    assert body["atual"]["inicio"] == "2025-01"
    assert body["atual"]["fim"] == "2025-12"
    assert body["anterior"]["inicio"] == "2024-01"
    assert body["anterior"]["fim"] == "2024-12"
    assert len(body["mensal"]["atual"]) == len(body["mensal"]["anterior"]) == 12
    assert len(body["por_classe"]) == 5


@pytest.mark.parametrize(
    ("months", "inicio", "previous_start", "previous_end"),
    [
        (3, "2025-10", "2025-07", "2025-09"),
        (6, "2025-07", "2025-01", "2025-06"),
        (12, "2025-01", "2024-01", "2024-12"),
    ],
)
def test_janelas_consecutivas_ancoradas_na_gold(
    months: int, inicio: str, previous_start: str, previous_end: str
) -> None:
    body = get_response({"inicio": inicio, "fim": "2025-12"}).json()

    assert body["atual"]["inicio"] == inicio
    assert body["atual"]["fim"] == "2025-12"
    assert body["anterior"]["inicio"] == previous_start
    assert body["anterior"]["fim"] == previous_end
    assert len(body["mensal"]["atual"]) == months
    assert len(body["mensal"]["anterior"]) == months
    assert [row["mes_referencia"] for row in body["mensal"]["atual"]] == sorted(
        row["mes_referencia"] for row in body["mensal"]["atual"]
    )


def test_agregacoes_preco_ucs_e_receita_por_classe() -> None:
    body = get_response().json()

    assert body["atual"]["receita_faturada"] == pytest.approx(150.0)
    assert body["atual"]["consumo_kwh"] == pytest.approx(35.0)
    assert body["atual"]["preco_medio_kwh"] == pytest.approx(150.0 / 35.0)
    assert body["atual"]["ucs_faturadas"] == 2
    assert body["atual"]["faturas"] == 12
    assert body["atual"]["faturas_atrasadas"] == 5
    assert body["anterior"]["receita_faturada"] == pytest.approx(20.0)
    assert body["anterior"]["ucs_faturadas"] == 5
    assert body["mensal"]["atual"][0] == {
        "mes_referencia": "2025-01",
        "receita_faturada": None,
        "consumo_kwh": None,
    }
    assert body["mensal"]["atual"][9] == {
        "mes_referencia": "2025-10",
        "receita_faturada": 0.0,
        "consumo_kwh": 0.0,
    }
    by_class = {row["classe"]: row for row in body["por_classe"]}
    assert by_class["RESIDENCIAL"]["receita_faturada"] == pytest.approx(120.0)
    assert by_class["COMERCIAL"]["receita_faturada"] == pytest.approx(30.0)
    assert by_class["RURAL"]["receita_faturada"] is None
    assert sum(
        row["receita_faturada"] or 0 for row in body["por_classe"]
    ) == pytest.approx(body["atual"]["receita_faturada"])


def test_consumo_zero_mantem_preco_nulo_e_zero_publicado() -> None:
    body = get_response({"inicio": "2025-10", "fim": "2025-12"}).json()
    assert body["mensal"]["atual"][0]["consumo_kwh"] == 0.0

    class ZeroConsumptionGold(MetricsGoldFake):
        def get_monthly_metrics(
            self, inicio: date, fim: date
        ) -> list[dict[str, object]]:
            rows = super().get_monthly_metrics(inicio, fim)
            for row in rows:
                if row["competencia"] == date(2025, 12, 1):
                    row["consumo_kwh"] = 0.0
            return [row for row in rows if row["competencia"] == date(2025, 12, 1)]

    body = get_response(
        {"inicio": "2025-10", "fim": "2025-12"}, ZeroConsumptionGold()
    ).json()
    assert body["atual"]["receita_faturada"] == 30.0
    assert body["atual"]["consumo_kwh"] == 0.0
    assert body["atual"]["preco_medio_kwh"] is None


class EmptyMetricsGold(MetricsGoldFake):
    def get_monthly_metrics(self, inicio: date, fim: date) -> list[dict[str, object]]:
        return []

    def get_class_revenue(self, inicio: date, fim: date) -> list[dict[str, object]]:
        return []


def test_calendario_valido_sem_medidas_retorna_null() -> None:
    body = get_response(gold=EmptyMetricsGold()).json()
    assert body["atual"]["receita_faturada"] is None
    assert body["atual"]["consumo_kwh"] is None
    assert body["atual"]["faturas"] is None
    assert body["atual"]["ucs_faturadas"] is None
    assert all(row["receita_faturada"] is None for row in body["mensal"]["atual"])
    assert all(row["receita_faturada"] is None for row in body["por_classe"])


@pytest.mark.parametrize(
    "params",
    [
        {"inicio": "2025-10"},
        {"fim": "2025-12"},
        {"inicio": "", "fim": "2025-12"},
        {"inicio": "2025-13", "fim": "2025-12"},
        # 25 meses: passa do máximo de 24
        {"inicio": "2023-12", "fim": "2025-12"},
        {"inicio": "2025-12", "fim": "2025-11"},
        {"inicio": "2026-01", "fim": "2025-12"},
        # Termina depois do último mês da base
        {"inicio": "2025-11", "fim": "2026-01"},
    ],
)
def test_periodo_invalido_retorna_422(params: dict[str, str]) -> None:
    assert get_response(params).status_code == 422


@pytest.mark.parametrize(
    ("inicio", "fim", "previous_start", "previous_end"),
    [
        # Qualquer tamanho de 1 a 24 meses
        ("2025-12", "2025-12", "2025-11", "2025-11"),
        ("2025-01", "2025-12", "2024-01", "2024-12"),
        ("2025-04", "2025-06", "2025-01", "2025-03"),
        ("2024-07", "2024-12", "2024-01", "2024-06"),
        ("2024-07", "2024-09", "2024-04", "2024-06"),
    ],
)
def test_periodo_pode_terminar_antes_do_ultimo_mes_da_base(
    inicio: str, fim: str, previous_start: str, previous_end: str
) -> None:
    response = get_response({"inicio": inicio, "fim": fim})

    assert response.status_code == 200
    body = response.json()
    assert (body["atual"]["inicio"], body["atual"]["fim"]) == (inicio, fim)
    assert (body["anterior"]["inicio"], body["anterior"]["fim"]) == (
        previous_start,
        previous_end,
    )


@pytest.mark.parametrize("consumo", [None, -2.0])
def test_preco_nulo_quando_consumo_nao_positivo_ou_ausente(
    consumo: float | None,
) -> None:
    class NonPositiveGold(MetricsGoldFake):
        def get_monthly_metrics(
            self, inicio: date, fim: date
        ) -> list[dict[str, object]]:
            rows = super().get_monthly_metrics(inicio, fim)
            for row in rows:
                if row["competencia"] == date(2025, 12, 1):
                    row["consumo_kwh"] = consumo
            return [row for row in rows if row["competencia"] == date(2025, 12, 1)]

    body = get_response(
        {"inicio": "2025-10", "fim": "2025-12"}, NonPositiveGold()
    ).json()
    assert body["atual"]["receita_faturada"] == 30.0
    assert body["atual"]["consumo_kwh"] == consumo
    assert body["atual"]["preco_medio_kwh"] is None


def test_falha_de_consulta_nao_vira_medidas_vazias_e_fecha_contexto() -> None:
    class FailingGold(MetricsGoldFake):
        def get_monthly_metrics(
            self, inicio: date, fim: date
        ) -> list[dict[str, object]]:
            raise RuntimeError("falha simulada")

    class TrackedContext:
        def __init__(self, gold: MetricsGoldFake) -> None:
            self.gold = gold
            self.closed = False

        def __enter__(self) -> MetricsGoldFake:
            return self.gold

        def __exit__(self, *args: object) -> None:
            self.closed = True

    success = TrackedContext(MetricsGoldFake())
    failure = TrackedContext(FailingGold())
    contexts = iter((success, failure))
    app.dependency_overrides[get_metrics_repository] = lambda: next(contexts)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        assert client.get("/api/metrics/general").status_code == 200
        response = client.get("/api/metrics/general")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert success.closed
    assert failure.closed


def test_calendario_sem_duas_janelas_nao_retorna_200_parcial() -> None:
    class ShortCalendarGold(MetricsGoldFake):
        def get_calendar(self) -> list[tuple[date, str]]:
            return [
                (date(2025, month, 1), f"2025-{month:02d}") for month in range(1, 13)
            ]

    app.dependency_overrides[get_metrics_repository] = lambda: nullcontext(
        ShortCalendarGold()
    )
    try:
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/metrics/general"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"].startswith("Recorte temporal indisponível:")


class FilteredMetricsGoldFake(MetricsGoldFake):
    """Células disjuntas em dois municípios para exercitar o recorte HTTP."""

    cells = (
        ("2025-09", "Recife", "RESIDENCIAL", 20.0, 10.0, 2, 2, 1),
        ("2025-09", "Olinda", "RESIDENCIAL", 30.0, 15.0, 3, 3, 0),
        ("2025-10", "Recife", "RURAL", 0.0, 0.0, 0, 0, 0),
        ("2025-11", "Recife", "RESIDENCIAL", 40.0, 20.0, 4, 4, 1),
        ("2025-11", "Recife", "COMERCIAL", 10.0, 5.0, 1, 1, 0),
        ("2025-11", "Olinda", "RESIDENCIAL", 60.0, 30.0, 6, 6, 2),
        ("2025-11", "Olinda", "COMERCIAL", 15.0, 5.0, 1, 1, 0),
        ("2025-12", "Recife", "RESIDENCIAL", 80.0, 40.0, 8, 8, 2),
        ("2025-12", "Recife", "COMERCIAL", 20.0, 10.0, 2, 2, 0),
        ("2025-12", "Olinda", "RESIDENCIAL", 100.0, 50.0, 10, 10, 3),
        ("2025-12", "Olinda", "COMERCIAL", 25.0, 5.0, 1, 1, 1),
    )

    def get_municipios(self) -> list[str]:
        return ["Cabo de Santo Agostinho", "Olinda", "Recife"]

    def _selected(
        self, inicio: date, fim: date, municipio: str | None, classe: str | None
    ) -> list[tuple]:
        return [
            cell
            for cell in self.cells
            if inicio <= date.fromisoformat(f"{cell[0]}-01") <= fim
            and (municipio is None or cell[1] == municipio)
            and (classe is None or cell[2] == classe)
        ]

    def get_monthly_metrics(
        self,
        inicio: date,
        fim: date,
        municipio: str | None = None,
        classe: str | None = None,
    ) -> list[dict[str, object]]:
        grouped: dict[date, dict[str, object]] = {}
        for (
            month,
            city,
            category,
            revenue,
            consumption,
            ucs,
            invoices,
            overdue,
        ) in self._selected(inicio, fim, municipio, classe):
            competence = date.fromisoformat(f"{month}-01")
            row = grouped.setdefault(
                competence,
                {
                    "competencia": competence,
                    "receita_faturada": 0.0,
                    "consumo_kwh": 0.0,
                    "ucs_faturadas": 0,
                    "faturas": 0,
                    "faturas_atrasadas": 0,
                },
            )
            row["receita_faturada"] += revenue
            row["consumo_kwh"] += consumption
            row["ucs_faturadas"] += ucs
            row["faturas"] += invoices
            row["faturas_atrasadas"] += overdue
        return list(grouped.values())

    def get_class_revenue(
        self,
        inicio: date,
        fim: date,
        municipio: str | None = None,
        classe: str | None = None,
    ) -> list[dict[str, object]]:
        grouped: dict[tuple[date, str], float] = {}
        for month, city, category, revenue, *_ in self._selected(
            inicio, fim, municipio, classe
        ):
            key = (date.fromisoformat(f"{month}-01"), category)
            grouped[key] = grouped.get(key, 0.0) + revenue
        return [
            {"competencia": month, "classe": category, "receita_faturada": revenue}
            for (month, category), revenue in grouped.items()
        ]


def test_municipio_isolado_restringe_os_quatro_grupos() -> None:
    body = get_response(
        {"inicio": "2025-10", "fim": "2025-12", "municipio": "Recife"},
        FilteredMetricsGoldFake(),
    ).json()

    assert body["atual"]["receita_faturada"] == pytest.approx(150.0)
    assert body["atual"]["consumo_kwh"] == pytest.approx(75.0)
    assert body["atual"]["preco_medio_kwh"] == pytest.approx(2.0)
    assert body["atual"]["ucs_faturadas"] == 10
    assert body["atual"]["faturas"] == 15
    assert body["atual"]["faturas_atrasadas"] == 3
    assert body["anterior"]["receita_faturada"] == pytest.approx(20.0)
    assert [item["receita_faturada"] for item in body["mensal"]["atual"]] == [
        0.0,
        50.0,
        100.0,
    ]
    by_class = {item["classe"]: item for item in body["por_classe"]}
    assert by_class["RESIDENCIAL"]["receita_faturada"] == pytest.approx(120.0)
    assert by_class["COMERCIAL"]["receita_faturada"] == pytest.approx(30.0)
    assert by_class["RURAL"]["receita_faturada"] == 0.0


def test_classe_isolada_restringe_resumos_series_e_por_classe() -> None:
    response = get_response(
        {"inicio": "2025-10", "fim": "2025-12", "classe": "COMERCIAL"},
        FilteredMetricsGoldFake(),
    )
    assert response.status_code == 200
    body = response.json()

    assert body["atual"]["receita_faturada"] == pytest.approx(70.0)
    assert body["atual"]["consumo_kwh"] == pytest.approx(25.0)
    assert body["atual"]["preco_medio_kwh"] == pytest.approx(2.8)
    assert body["atual"]["ucs_faturadas"] == 3
    assert body["atual"]["faturas"] == 5
    assert body["atual"]["faturas_atrasadas"] == 1
    assert body["anterior"]["receita_faturada"] is None
    assert [item["receita_faturada"] for item in body["mensal"]["atual"]] == [
        None,
        25.0,
        45.0,
    ]
    assert body["por_classe"] == [
        {
            "classe": "COMERCIAL",
            "receita_faturada": 70.0,
            "receita_faturada_anterior": None,
        }
    ]


def test_parametro_repetido_retorna_422_antes_da_conexao() -> None:
    class UnexpectedContext:
        def __enter__(self):
            raise AssertionError("a conexão não deve ser aberta")

        def __exit__(self, *args: object) -> None:
            pass

    app.dependency_overrides[get_metrics_repository] = lambda: UnexpectedContext()
    try:
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/metrics/general?municipio=Recife&municipio=Olinda"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_municipio_e_classe_combinados_usam_o_mesmo_recorte() -> None:
    response = get_response(
        {
            "inicio": "2025-10",
            "fim": "2025-12",
            "municipio": "Recife",
            "classe": "COMERCIAL",
        },
        FilteredMetricsGoldFake(),
    )
    assert response.status_code == 200
    body = response.json()

    assert body["atual"]["receita_faturada"] == pytest.approx(30.0)
    assert body["atual"]["consumo_kwh"] == pytest.approx(15.0)
    assert body["atual"]["preco_medio_kwh"] == pytest.approx(2.0)
    assert body["atual"]["ucs_faturadas"] == 2
    assert body["atual"]["faturas"] == 3
    assert body["atual"]["faturas_atrasadas"] == 0
    assert body["anterior"]["receita_faturada"] is None
    assert [item["receita_faturada"] for item in body["mensal"]["atual"]] == [
        None,
        10.0,
        20.0,
    ]
    assert body["por_classe"] == [
        {
            "classe": "COMERCIAL",
            "receita_faturada": 30.0,
            "receita_faturada_anterior": None,
        }
    ]


def test_categorias_omitidas_e_vazias_sao_equivalentes() -> None:
    period = {"inicio": "2025-10", "fim": "2025-12"}
    omitted = get_response(period, FilteredMetricsGoldFake())
    empty = get_response(
        {**period, "municipio": "", "classe": ""}, FilteredMetricsGoldFake()
    )

    assert omitted.status_code == empty.status_code == 200
    assert omitted.json() == empty.json()
    assert len(empty.json()["por_classe"]) == 5


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("municipio", "Desconhecido"),
        ("municipio", "recife"),
        ("municipio", " Recife "),
        ("municipio", "   "),
        ("classe", "DESCONHECIDA"),
        ("classe", "residencial"),
        ("classe", " RESIDENCIAL "),
        ("classe", "   "),
    ],
)
def test_categoria_desconhecida_ou_espacos_retorna_422(field: str, value: str) -> None:
    response = get_response({field: value}, FilteredMetricsGoldFake())
    assert response.status_code == 422


@pytest.mark.parametrize(
    "query",
    [
        "inicio=2025-10&inicio=2025-10&fim=2025-12",
        "inicio=2025-10&fim=2025-12&fim=2025-12",
        "municipio=Recife&municipio=Recife",
        "municipio=&municipio=",
        "classe=COMERCIAL&classe=COMERCIAL",
        "classe=&classe=",
        "bairro=Boa%20Viagem",
        "periodo=12",
        "foo=",
    ],
)
def test_query_parameter_repetido_ou_desconhecido_retorna_422(
    query: str,
) -> None:
    app.dependency_overrides[get_metrics_repository] = lambda: nullcontext(
        FilteredMetricsGoldFake()
    )
    try:
        response = TestClient(app).get(f"/api/metrics/general?{query}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("filters", "expected_classes"),
    [
        ({"municipio": "Cabo de Santo Agostinho"}, 5),
        ({"classe": "INDUSTRIAL"}, 1),
        (
            {"municipio": "Cabo de Santo Agostinho", "classe": "INDUSTRIAL"},
            1,
        ),
    ],
)
def test_recorte_valido_sem_celulas_mantem_null(
    filters: dict[str, str], expected_classes: int
) -> None:
    response = get_response(
        {"inicio": "2025-10", "fim": "2025-12", **filters},
        FilteredMetricsGoldFake(),
    )
    assert response.status_code == 200
    body = response.json()

    for window in ("atual", "anterior"):
        assert all(
            body[window][field] is None
            for field in (
                "receita_faturada",
                "consumo_kwh",
                "preco_medio_kwh",
                "ucs_faturadas",
                "faturas",
                "faturas_atrasadas",
            )
        )
        assert len(body["mensal"][window]) == 3
        assert all(
            point["receita_faturada"] is None and point["consumo_kwh"] is None
            for point in body["mensal"][window]
        )
    assert len(body["por_classe"]) == expected_classes
    assert all(
        row["receita_faturada"] is None and row["receita_faturada_anterior"] is None
        for row in body["por_classe"]
    )


@pytest.mark.parametrize(
    "filters",
    [
        {},
        {"municipio": "Recife"},
        {"classe": "RESIDENCIAL"},
        {"municipio": "Recife", "classe": "RESIDENCIAL"},
    ],
)
def test_receita_por_classe_concilia_com_total_no_mesmo_recorte(
    filters: dict[str, str],
) -> None:
    body = get_response(
        {"inicio": "2025-10", "fim": "2025-12", **filters},
        FilteredMetricsGoldFake(),
    ).json()

    for window, field in (
        ("atual", "receita_faturada"),
        ("anterior", "receita_faturada_anterior"),
    ):
        present = [row[field] for row in body["por_classe"] if row[field] is not None]
        if present:
            assert sum(present) == pytest.approx(body[window]["receita_faturada"])
        else:
            assert body[window]["receita_faturada"] is None


def get_error_response(gold: MetricsGoldFake):
    app.dependency_overrides[get_metrics_repository] = lambda: nullcontext(gold)
    try:
        return TestClient(app, raise_server_exceptions=False).get(
            "/api/metrics/general"
        )
    finally:
        app.dependency_overrides.clear()


def test_calendario_gold_vazio_retorna_503_especifico() -> None:
    class EmptyCalendarGold(MetricsGoldFake):
        def get_calendar(self) -> list[tuple[date, str]]:
            return []

    response = get_error_response(EmptyCalendarGold())

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Recorte temporal indisponível: o calendário Gold não possui competências suficientes para o período solicitado."
    }


def test_calendario_com_competencia_duplicada_retorna_503() -> None:
    class DuplicateCalendarGold(MetricsGoldFake):
        def get_calendar(self) -> list[tuple[date, str]]:
            months = super().get_calendar()
            return [*months, months[-1]]

    response = get_error_response(DuplicateCalendarGold())

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Recorte temporal indisponível: o calendário Gold não possui competências suficientes para o período solicitado."
    }


def test_calendario_com_rotulo_inconsistente_retorna_503() -> None:
    class WrongLabelGold(MetricsGoldFake):
        def get_calendar(self) -> list[tuple[date, str]]:
            return [
                (month, "2025-11" if month == date(2025, 12, 1) else label)
                for month, label in super().get_calendar()
            ]

    response = get_error_response(WrongLabelGold())

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Recorte temporal indisponível: o calendário Gold não possui competências suficientes para o período solicitado."
    }


def test_erro_inesperado_de_programacao_nao_vira_422() -> None:
    class UnexpectedGold(MetricsGoldFake):
        def get_classes(self) -> list[str]:
            raise ValueError("consulta interna e credencial privada")

    response = get_error_response(UnexpectedGold())

    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno"}
    assert "consulta interna" not in response.text
    assert "credencial" not in response.text


def test_configuracao_gold_ausente_retorna_503_sem_vazamento(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @contextmanager
    def missing_connection():
        raise RuntimeError("DATABASE_URL não configurada")
        yield

    monkeypatch.setattr(metrics_controller, "get_connection", missing_connection)
    response = TestClient(app, raise_server_exceptions=False).get(
        "/api/metrics/general"
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Gold indisponível"}
    assert "DATABASE_URL" not in response.text


@pytest.mark.parametrize("error", ["operational", "timeout"])
def test_gold_indisponivel_retorna_503_sem_detalhes(error: str) -> None:
    from sqlalchemy.exc import OperationalError, TimeoutError

    class UnavailableGold(MetricsGoldFake):
        def get_calendar(self) -> list[tuple[date, str]]:
            if error == "operational":
                raise OperationalError("SQL privado", {}, Exception("senha privada"))
            raise TimeoutError("timeout com credencial privada")

    response = get_error_response(UnavailableGold())
    assert response.status_code == 503
    assert response.json() == {"detail": "Gold indisponível"}
    assert "privad" not in response.text


def test_resposta_gold_invalida_retorna_500_generico() -> None:
    class InvalidGold(MetricsGoldFake):
        def get_classes(self) -> list[str]:
            return ["RESIDENCIAL", None]

    response = get_error_response(InvalidGold())
    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno"}


def test_openapi_documenta_erros_e_contrato_de_indicadores() -> None:
    document = TestClient(app).get("/api/openapi.json").json()
    operation = document["paths"]["/api/metrics/general"]["get"]
    assert {item["name"] for item in operation["parameters"]} == {
        "inicio",
        "fim",
        "municipio",
        "classe",
    }
    assert all(not item["required"] for item in operation["parameters"])
    assert {"200", "422", "503", "500"} <= set(operation["responses"])
    examples = operation["responses"]["503"]["content"]["application/json"]["examples"]
    details = {entry["value"]["detail"] for entry in examples.values()}
    assert details == {
        "Gold indisponível",
        "Recorte temporal indisponível: o calendário Gold não possui competências suficientes para o período solicitado.",
    }
    schema_ref = operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ]
    schema = document["components"]["schemas"][schema_ref.rsplit("/", 1)[-1]]
    assert set(schema["properties"]) == {"atual", "anterior", "mensal", "por_classe"}


def test_calendario_com_lacuna_retorna_503_especifico() -> None:
    class GapGold(MetricsGoldFake):
        def get_calendar(self) -> list[tuple[date, str]]:
            return [row for row in super().get_calendar() if row[0] != date(2025, 6, 1)]

    response = get_error_response(GapGold())
    assert response.status_code == 503
    assert response.json()["detail"].startswith("Recorte temporal indisponível:")


def test_contexto_fecha_em_falha_de_calendario_e_de_banco() -> None:
    from sqlalchemy.exc import OperationalError

    class EmptyCalendarGold(MetricsGoldFake):
        def get_calendar(self) -> list[tuple[date, str]]:
            return []

    class UnavailableGold(MetricsGoldFake):
        def get_calendar(self) -> list[tuple[date, str]]:
            raise OperationalError("SQL privado", {}, Exception("senha privada"))

    class TrackedContext:
        def __init__(self, gold: MetricsGoldFake) -> None:
            self.gold = gold
            self.closed = False

        def __enter__(self) -> MetricsGoldFake:
            return self.gold

        def __exit__(self, *args: object) -> None:
            self.closed = True

    contexts = [TrackedContext(EmptyCalendarGold()), TrackedContext(UnavailableGold())]
    source = iter(contexts)
    app.dependency_overrides[get_metrics_repository] = lambda: next(source)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        assert client.get("/api/metrics/general").status_code == 503
        assert client.get("/api/metrics/general").status_code == 503
    finally:
        app.dependency_overrides.clear()
    assert all(context.closed for context in contexts)


def test_periodo_de_tamanho_invalido_com_calendario_vazio_retorna_422() -> None:
    class EmptyCalendarGold(MetricsGoldFake):
        def get_calendar(self) -> list[tuple[date, str]]:
            return []

    response = get_response(
        {"inicio": "2023-12", "fim": "2025-12"}, EmptyCalendarGold()
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "params",
    [
        {"inicio": "2023-12", "fim": "2025-12"},
        {"inicio": "2025-12", "fim": "2025-10"},
        {"inicio": "2025-13", "fim": "2025-12"},
        {"inicio": "2025-10"},
        {"inicio": "", "fim": "2025-12"},
    ],
)
def test_periodo_invalido_retorna_422_sem_abrir_conexao(
    params: dict[str, str],
) -> None:
    from sqlalchemy.exc import OperationalError

    class UnavailableContext:
        def __enter__(self):
            raise OperationalError("SQL privado", {}, Exception("Gold indisponível"))

        def __exit__(self, *args: object) -> None:
            pass

    app.dependency_overrides[get_metrics_repository] = lambda: UnavailableContext()
    try:
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/metrics/general", params=params
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_janela_valida_com_calendario_insuficiente_retorna_503_especifico() -> None:
    class ShortCalendarGold(MetricsGoldFake):
        def get_calendar(self) -> list[tuple[date, str]]:
            return [row for row in super().get_calendar() if row[0] >= date(2025, 9, 1)]

    response = get_response(
        {"inicio": "2025-10", "fim": "2025-12"}, ShortCalendarGold()
    )
    assert response.status_code == 503
    assert response.json() == {
        "detail": "Recorte temporal indisponível: o calendário Gold não possui competências suficientes para o período solicitado."
    }


def test_janela_valida_com_gold_indisponivel_retorna_503_generico() -> None:
    from sqlalchemy.exc import OperationalError

    class UnavailableContext:
        def __enter__(self):
            raise OperationalError("SQL privado", {}, Exception("senha privada"))

        def __exit__(self, *args: object) -> None:
            pass

    app.dependency_overrides[get_metrics_repository] = lambda: UnavailableContext()
    try:
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/metrics/general",
            params={"inicio": "2025-10", "fim": "2025-12"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Gold indisponível"}
