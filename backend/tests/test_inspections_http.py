"""Contrato HTTP da fila de suspeitas publicada pela Gold."""

from contextlib import nullcontext
from datetime import date

from fastapi.testclient import TestClient

from app.main import app


class NoActiveOrders:
    def get_active_orders(self, ids_uc):
        return []


def test_fila_gold_retorna_contrato_e_prioridade_publicada() -> None:
    from app.controllers.inspections import get_inspections_repository

    class GoldFake:
        orders = NoActiveOrders()

        def get_snapshot_date(self) -> date:
            return date(2026, 6, 1)

        def get_catalog(self) -> tuple[list[tuple[str, str | None]], list[str]]:
            return [("Recife", "Boa Viagem")], ["RESIDENCIAL"]

        def get_summary(self, municipio, bairro, classe):
            return {"ucs": 1, "medidas": 1, "kwh_recuperavel_estimado_ano": 1380.5}

        def get_items(self, municipio, bairro, classe, limite, offset):
            return [
                {
                    "prioridade": 27,
                    "id_uc": "UC123456",
                    "score": 55,
                    "motivo_suspeita": "Queda; Medidor",
                    "kwh_recuperavel_estimado_ano": 1380.5,
                    "municipio": "Recife",
                    "bairro": "Boa Viagem",
                    "classe": "RESIDENCIAL",
                }
            ]

    app.dependency_overrides[get_inspections_repository] = lambda: nullcontext(
        GoldFake()
    )
    try:
        response = TestClient(app).get("/api/inspections/queue")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "data_referencia": "2026-06-01",
        "resumo": {"ucs": 1, "kwh_recuperavel_estimado_ano": 1380.5},
        "pagina": 1,
        "limite": 20,
        "total": 1,
        "itens": [
            {
                "prioridade": 27,
                "id_uc": "UC123456",
                "score": 55,
                "motivo_suspeita": "Queda; Medidor",
                "kwh_recuperavel_estimado_ano": 1380.5,
                "municipio": "Recife",
                "bairro": "Boa Viagem",
                "classe": "RESIDENCIAL",
                "ordem_aberta": None,
            }
        ],
    }


class QueueGoldFake:
    orders = NoActiveOrders()

    rows = (
        (
            2,
            "UC000002",
            90,
            "Motivo A; Motivo B",
            100.25,
            "Recife",
            "Boa Viagem",
            "RESIDENCIAL",
        ),
        (7, "UC000007", 72, "Motivo C", 20.0, "Recife", "Casa Forte", "COMERCIAL"),
        (9, "UC000009", 60, "Motivo D", 50.5, "Olinda", "Bairro Novo", "RESIDENCIAL"),
        (12, "UC000012", 30, "Motivo E", 0.0, "Recife", "Boa Viagem", "RESIDENCIAL"),
    )
    columns = (
        "prioridade",
        "id_uc",
        "score",
        "motivo_suspeita",
        "kwh_recuperavel_estimado_ano",
        "municipio",
        "bairro",
        "classe",
    )

    def __init__(self, snapshot=date(2026, 6, 1), rows=None):
        self.snapshot = snapshot
        self.data = [
            dict(zip(self.columns, row, strict=True))
            for row in (rows if rows is not None else self.rows)
        ]
        self.page_calls = 0

    def get_catalog(self):
        return [
            ("Recife", "Boa Viagem"),
            ("Recife", "Casa Forte"),
            ("Olinda", "Bairro Novo"),
            ("Jaboatão", "Piedade"),
        ], ["RESIDENCIAL", "COMERCIAL", "INDUSTRIAL"]

    def get_snapshot_date(self):
        return self.snapshot

    def matching(self, municipio, bairro, classe):
        return [
            row
            for row in self.data
            if (municipio is None or row["municipio"] == municipio)
            and (bairro is None or row["bairro"] == bairro)
            and (classe is None or row["classe"] == classe)
        ]

    def get_summary(self, municipio, bairro, classe):
        rows = self.matching(municipio, bairro, classe)
        values = [row["kwh_recuperavel_estimado_ano"] for row in rows]
        return {
            "ucs": len(rows),
            "medidas": sum(value is not None for value in values),
            "kwh_recuperavel_estimado_ano": sum(values)
            if rows and all(value is not None for value in values)
            else None,
        }

    def get_items(self, municipio, bairro, classe, limite, offset):
        self.page_calls += 1
        return sorted(
            self.matching(municipio, bairro, classe),
            key=lambda row: (row["prioridade"], row["id_uc"]),
        )[offset : offset + limite]


def queue_response(params=None, gold=None):
    from app.controllers.inspections import get_inspections_repository

    app.dependency_overrides[get_inspections_repository] = lambda: nullcontext(
        gold if gold is not None else QueueGoldFake()
    )
    try:
        return TestClient(app, raise_server_exceptions=False).get(
            "/api/inspections/queue", params=params
        )
    finally:
        app.dependency_overrides.clear()


def test_resumo_cobre_recorte_nao_pagina_e_prioridade_global():
    body = queue_response({"municipio": "Recife", "limite": 1, "pagina": 2}).json()
    assert body["resumo"] == {"ucs": 3, "kwh_recuperavel_estimado_ano": 120.25}
    assert body["total"] == 3
    assert (body["pagina"], body["limite"]) == (2, 1)
    assert [(item["prioridade"], item["id_uc"]) for item in body["itens"]] == [
        (7, "UC000007")
    ]
    assert body["itens"][0]["ordem_aberta"] is None
    assert "nome_titular" not in body["itens"][0]


def test_filtros_individuais_combinados_e_vazios():
    cases = [
        ({"municipio": "Recife"}, [2, 7, 12], 120.25),
        ({"classe": "RESIDENCIAL"}, [2, 9, 12], 150.75),
        ({"municipio": "Recife", "bairro": "Boa Viagem"}, [2, 12], 100.25),
        ({"municipio": "Recife", "bairro": "Boa Viagem", "classe": "COMERCIAL"}, [], 0),
        ({"municipio": "", "bairro": "", "classe": ""}, [2, 7, 9, 12], 170.75),
    ]
    for params, priorities, energy in cases:
        response = queue_response(params)
        assert response.status_code == 200
        body = response.json()
        assert [item["prioridade"] for item in body["itens"]] == priorities
        assert body["total"] == len(priorities)
        assert body["resumo"]["kwh_recuperavel_estimado_ano"] == energy
        assert body["data_referencia"] == "2026-06-01"


def test_recorte_vazio_e_pagina_extrema():
    assert queue_response({"municipio": "Jaboatão"}).json() == {
        "data_referencia": "2026-06-01",
        "resumo": {"ucs": 0, "kwh_recuperavel_estimado_ano": 0.0},
        "pagina": 1,
        "limite": 20,
        "total": 0,
        "itens": [],
    }
    gold = QueueGoldFake()
    response = queue_response({"pagina": str(10**18)}, gold)
    assert response.status_code == 200
    assert response.json()["total"] == 4
    assert response.json()["resumo"]["kwh_recuperavel_estimado_ano"] == 170.75
    assert response.json()["itens"] == []
    assert gold.page_calls == 0


def test_parametros_invalidos_e_repetidos():
    cases = [
        {"bairro": "Boa Viagem"},
        {"municipio": "Olinda", "bairro": "Boa Viagem"},
        {"municipio": "Desconhecido"},
        {"classe": "DESCONHECIDA"},
        {"pagina": "0"},
        {"limite": "0"},
        {"limite": "51"},
        {"limite": "abc"},
        {"motivo": "x"},
        [("municipio", "Recife"), ("municipio", "Olinda")],
        [("pagina", "1"), ("pagina", "2")],
    ]
    for params in cases:
        assert queue_response(params).status_code == 422, params


def test_snapshot_vazio_e_medida_obrigatoria_ausente():
    response = queue_response(gold=QueueGoldFake(rows=[], snapshot=None))
    assert response.status_code == 503
    assert response.json() == {"detail": "Fila Gold indisponível"}
    gold = QueueGoldFake()
    gold.data[0]["kwh_recuperavel_estimado_ano"] = None
    response = queue_response(gold=gold)
    assert response.status_code == 503
    assert response.json() == {"detail": "Fila Gold indisponível"}


def test_falha_postgresql_e_erro_inesperado_sao_seguros():
    from sqlalchemy.exc import OperationalError, ProgrammingError

    class FailingGold(QueueGoldFake):
        def __init__(self, error):
            super().__init__()
            self.error = error

        def get_snapshot_date(self):
            raise self.error

    for error, status in (
        (OperationalError("SELECT segredo", {}, Exception("senha")), 503),
        (ProgrammingError("SELECT segredo", {}, Exception("coluna privada")), 500),
    ):
        response = queue_response(gold=FailingGold(error))
        assert response.status_code == status
        assert response.json() == {
            "detail": "Gold indisponível" if status == 503 else "Erro interno"
        }
        assert "segredo" not in response.text


def test_configuracao_ausente_e_contexto_liberado(monkeypatch):
    from contextlib import contextmanager

    from app.controllers.inspections import get_inspections_repository

    class TrackedContext:
        def __init__(self, gold):
            self.gold = gold
            self.closed = False

        def __enter__(self):
            return self.gold

        def __exit__(self, *_args):
            self.closed = True

    success = TrackedContext(QueueGoldFake())
    failure = TrackedContext(QueueGoldFake(rows=[], snapshot=None))
    contexts = iter((success, failure))
    app.dependency_overrides[get_inspections_repository] = lambda: next(contexts)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        assert client.get("/api/inspections/queue").status_code == 200
        assert client.get("/api/inspections/queue").status_code == 503
    finally:
        app.dependency_overrides.clear()
    assert success.closed and failure.closed

    @contextmanager
    def missing_config():
        raise RuntimeError("DATABASE_URL não configurada")
        yield

    from app.controllers import inspections as inspections_controller

    monkeypatch.setattr(inspections_controller, "get_connection", missing_config)
    client = TestClient(app, raise_server_exceptions=False)
    invalid = client.get("/api/inspections/queue", params={"bairro": "Boa Viagem"})
    assert invalid.status_code == 422
    response = client.get("/api/inspections/queue")
    assert response.status_code == 503
    assert response.json() == {"detail": "Gold indisponível"}


def test_openapi_e_regressao_health():
    client = TestClient(app)
    paths = client.get("/api/openapi.json").json()["paths"]
    assert "/api/inspections/queue" in paths
    assert "/api/api/inspections/queue" not in paths
    assert client.get("/api/api/inspections/queue").status_code == 404
    operation = paths["/api/inspections/queue"]["get"]
    assert set(operation["responses"]) >= {"200", "422", "503", "500"}
    params = {item["name"]: item for item in operation["parameters"]}
    assert set(params) == {
        "municipio",
        "bairro",
        "classe",
        "pagina",
        "limite",
        "vgrid360_access_token",
    }
    assert params["limite"]["schema"]["maximum"] == 50
    assert client.get("/api/health").status_code == 200
