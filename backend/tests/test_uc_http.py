"""Contrato HTTP da Visão 360, com cenários sintéticos e leitura Gold."""

from contextlib import nullcontext
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.controllers.uc import get_uc_repository
from app.core.config import get_settings
from app.exceptions.uc import GoldUnavailableError
from app.main import app


class GoldFake:
    def get_cadastro(self, uc_id: str) -> dict[str, object] | None:
        return {
            "id_uc": uc_id,
            "nome_titular": "Maria Exemplo",
            "logradouro": "Rua Exemplo",
            "numero": "10",
            "bairro": "Boa Viagem",
            "municipio": "Recife",
            "uf": "PE",
            "classe": "RESIDENCIAL",
            "id_medidor_atual": "MED001",
            "tipo_medidor_atual": "SMART",
            "modelo_medidor_atual": "SM-1",
            "data_instalacao_medidor_atual": date(2025, 9, 15),
            "possui_gd": False,
            "data_conexao_gd": None,
            "potencia_gd_kwp": None,
            "modalidade_gd": None,
            "cpf_cnpj_mascarado": "***1234",
        }

    def get_consumo_12m(self, uc_id: str) -> list[dict[str, object]]:
        return [
            {
                "mes_referencia": f"2025-{month:02d}"
                if month >= 7
                else f"2026-{month:02d}",
                "consumo_kwh": 205.0 if month == 6 else None,
                "consumo_ano_anterior_kwh": None,
                "variacao_ano_anterior_pct": None,
            }
            for month in (*range(7, 13), *range(1, 7))
        ]

    def get_leituras_page(
        self, uc_id: str, limite: int, offset: int
    ) -> tuple[int, list[dict[str, object]]]:
        return 1, [
            {
                "id_leitura": "LEI001",
                "id_medidor": "MED001",
                "mes_referencia": "2026-06",
                "data_leitura": date(2026, 6, 25),
                "leitura_anterior": None,
                "leitura_atual": 1405.0,
                "consumo_kwh": 205.0,
                "consumo_ano_anterior_kwh": None,
                "variacao_ano_anterior_pct": None,
                "tipo_leitura": "ESTIMADA",
                "status_qualidade_leitura": "TROCA_DE_MEDIDOR",
                "consumo_imputado": True,
            }
        ]

    def get_faturas_em_aberto(self, uc_id: str) -> list[dict[str, object]]:
        return [
            {
                "id_fatura": "FT001",
                "mes_referencia": "2026-06",
                "data_vencimento": date(2026, 7, 12),
                "receita_faturada": 185.501,
                "status_pagamento": "PENDENTE",
            }
        ]

    def get_resumo_faturas_em_aberto(self, uc_id: str) -> tuple[int, float | None]:
        return 1, 185.501

    def get_faturas_page(
        self, uc_id: str, limite: int, offset: int
    ) -> tuple[int, list[dict[str, object]]]:
        return 1, [
            {
                "id_fatura": "FT001",
                "mes_referencia": "2026-06",
                "consumo_kwh": 205.0,
                "bandeira_tarifaria": "VERDE",
                "receita_faturada": 185.501,
                "data_vencimento": date(2026, 7, 12),
                "status_pagamento": "PENDENTE",
                "data_emissao": date(2026, 6, 30),
                "data_pagamento": None,
                "dias_atraso": 0,
            }
        ]

    def get_interrupcoes_page(
        self, uc_id: str, limite: int, offset: int
    ) -> tuple[int, list[dict[str, object]]]:
        return 1, [
            {
                "id_ocorrencia": "OCO001",
                "alimentador": "ALM-REC-008",
                "tipo": "FALTA DE ENERGIA",
                "causa": "VEGETACAO",
                "data_abertura": datetime(2026, 6, 2, 10),
                "data_encerramento": datetime(2026, 6, 2, 12, 30),
                "duracao_h": 2.5,
                "duracao_truncada": False,
            }
        ]

    def get_chamados_page(
        self, uc_id: str, limite: int, offset: int
    ) -> tuple[int, list[dict[str, object]]]:
        return 1, [
            {
                "protocolo": "PROT001",
                "assunto": "FATURA",
                "subassunto": "VALOR ALTO",
                "canal": "TELEFONE",
                "data_abertura": datetime(2026, 6, 16, 9),
                "data_fechamento": None,
                "status_chamado": "ABERTO",
                "qtd_tratativas": 2,
            }
        ]


@pytest.fixture
def http_gold() -> tuple[TestClient, GoldFake]:
    gold = GoldFake()
    app.dependency_overrides[get_uc_repository] = lambda: nullcontext(gold)
    with TestClient(app) as client:
        yield client, gold
    app.dependency_overrides.clear()


def test_visao_360_http_compoe_json_aprovado(
    http_gold: tuple[TestClient, GoldFake],
) -> None:
    client, _ = http_gold

    response = client.get("/api/uc/UC123456/360")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "uc",
        "medidor_atual",
        "geracao_distribuida",
        "faturas_em_aberto",
        "resumo_faturas_em_aberto",
        "consumo_12m",
        "historicos",
    }
    assert body["uc"] == {
        "id_uc": "UC123456",
        "nome_titular": "Maria Exemplo",
        "logradouro": "Rua Exemplo",
        "numero": "10",
        "bairro": "Boa Viagem",
        "municipio": "Recife",
        "uf": "PE",
        "classe": "RESIDENCIAL",
    }
    assert body["medidor_atual"]["data_instalacao_medidor_atual"] == "2025-09-15"
    assert body["geracao_distribuida"] == {
        "possui_gd": False,
        "data_conexao_gd": None,
        "potencia_gd_kwp": None,
        "modalidade_gd": None,
    }
    assert body["faturas_em_aberto"][0]["receita_faturada"] == 185.501
    assert body["resumo_faturas_em_aberto"] == {
        "quantidade": 1,
        "valor_total": 185.501,
    }
    assert len(body["consumo_12m"]) == 12
    assert body["consumo_12m"][0]["consumo_kwh"] is None
    assert body["consumo_12m"][-1]["consumo_kwh"] == 205.0
    assert set(body["historicos"]) == {
        "faturas",
        "interrupcoes",
        "chamados",
        "leituras",
    }
    assert body["historicos"]["faturas"]["itens"][0]["bandeira_tarifaria"] == "VERDE"
    assert body["historicos"]["interrupcoes"]["itens"][0]["duracao_h"] == 2.5
    assert (
        body["historicos"]["interrupcoes"]["itens"][0]["data_abertura"]
        == "2026-06-02T10:00:00"
    )
    assert body["historicos"]["chamados"]["itens"][0]["qtd_tratativas"] == 2
    assert body["historicos"]["leituras"]["itens"][0]["consumo_imputado"] is True
    assert set(body["historicos"]["faturas"]["itens"][0]) == {
        "id_fatura",
        "mes_referencia",
        "consumo_kwh",
        "bandeira_tarifaria",
        "receita_faturada",
        "data_vencimento",
        "status_pagamento",
        "data_emissao",
        "data_pagamento",
        "dias_atraso",
    }
    assert set(body["historicos"]["interrupcoes"]["itens"][0]) == {
        "id_ocorrencia",
        "alimentador",
        "tipo",
        "causa",
        "data_abertura",
        "data_encerramento",
        "duracao_h",
        "duracao_truncada",
    }
    assert set(body["historicos"]["chamados"]["itens"][0]) == {
        "protocolo",
        "assunto",
        "subassunto",
        "canal",
        "data_abertura",
        "data_fechamento",
        "status_chamado",
        "qtd_tratativas",
    }
    assert set(body["historicos"]["leituras"]["itens"][0]) == {
        "id_leitura",
        "id_medidor",
        "mes_referencia",
        "data_leitura",
        "leitura_anterior",
        "leitura_atual",
        "consumo_kwh",
        "consumo_ano_anterior_kwh",
        "variacao_ano_anterior_pct",
        "tipo_leitura",
        "status_qualidade_leitura",
        "consumo_imputado",
    }
    assert "cpf_cnpj_mascarado" not in response.text
    assert "insight" not in response.text
    assert "chat" not in response.text


def test_visao_360_http_uc_inexistente_404(
    http_gold: tuple[TestClient, GoldFake],
) -> None:
    client, _ = http_gold

    class MissingGold(GoldFake):
        def get_cadastro(self, uc_id: str) -> None:
            return None

        def get_faturas_em_aberto(self, uc_id: str) -> None:
            pytest.fail("UC ausente não consulta fatos")

    app.dependency_overrides[get_uc_repository] = lambda: nullcontext(MissingGold())

    response = client.get("/api/uc/UC999999/360")

    assert response.status_code == 404
    assert response.json() == {"detail": "Unidade consumidora não encontrada"}


@pytest.mark.parametrize(
    "url",
    [
        "/api/uc/123456/360",
        "/api/uc/UC12345/360",
        "/api/uc/UC123456/360?pagina_faturas=0",
        "/api/uc/UC123456/360?pagina_interrupcoes=0",
        "/api/uc/UC123456/360?pagina_chamados=invalid",
        "/api/uc/UC123456/360?pagina_leituras=-1",
        "/api/uc/UC123456/360?limite=0",
        "/api/uc/UC123456/360?limite=51",
    ],
)
def test_visao_360_http_entrada_invalida_422(
    http_gold: tuple[TestClient, GoldFake], url: str
) -> None:
    client, _ = http_gold

    response = client.get(url)

    assert response.status_code == 422
    assert "Maria Exemplo" not in response.text


def test_visao_360_http_paginas_independentes_sem_alterar_cartoes(
    http_gold: tuple[TestClient, GoldFake],
) -> None:
    client, _ = http_gold

    class PagedGold(GoldFake):
        def __init__(self) -> None:
            self.offsets: dict[str, list[int]] = {
                "faturas": [],
                "interrupcoes": [],
                "chamados": [],
                "leituras": [],
            }

        def get_faturas_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            self.offsets["faturas"].append(offset)
            return 1, super().get_faturas_page(uc_id, limite, offset)[
                1
            ] if offset == 0 else []

        def get_interrupcoes_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            self.offsets["interrupcoes"].append(offset)
            return 1, super().get_interrupcoes_page(uc_id, limite, offset)[
                1
            ] if offset == 0 else []

        def get_chamados_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            self.offsets["chamados"].append(offset)
            return 1, super().get_chamados_page(uc_id, limite, offset)[
                1
            ] if offset == 0 else []

        def get_leituras_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            self.offsets["leituras"].append(offset)
            return 1, super().get_leituras_page(uc_id, limite, offset)[
                1
            ] if offset == 0 else []

    gold = PagedGold()
    app.dependency_overrides[get_uc_repository] = lambda: nullcontext(gold)
    first = client.get("/api/uc/UC123456/360?limite=1").json()
    second_response = client.get("/api/uc/UC123456/360?limite=1&pagina_chamados=2")

    assert second_response.status_code == 200
    second = second_response.json()
    assert gold.offsets == {
        "faturas": [0, 0],
        "interrupcoes": [0, 0],
        "chamados": [0, 1],
        "leituras": [0, 0],
    }
    for field in (
        "uc",
        "medidor_atual",
        "geracao_distribuida",
        "faturas_em_aberto",
        "resumo_faturas_em_aberto",
        "consumo_12m",
    ):
        assert second[field] == first[field]
    for history in ("faturas", "interrupcoes", "leituras"):
        assert second["historicos"][history] == first["historicos"][history]
    assert second["historicos"]["chamados"] == {
        "pagina": 2,
        "limite": 1,
        "total": 1,
        "itens": [],
    }


def test_visao_360_http_ausencias_normais_preservam_nulos_e_zero(
    http_gold: tuple[TestClient, GoldFake],
) -> None:
    client, _ = http_gold

    class EmptyGold(GoldFake):
        def get_cadastro(self, uc_id: str) -> dict[str, object]:
            row = super().get_cadastro(uc_id)
            row["id_medidor_atual"] = None
            row["tipo_medidor_atual"] = None
            row["modelo_medidor_atual"] = None
            row["data_instalacao_medidor_atual"] = None
            return row

        def get_faturas_em_aberto(self, uc_id: str) -> list[dict[str, object]]:
            return []

        def get_resumo_faturas_em_aberto(self, uc_id: str) -> tuple[int, None]:
            return 0, None

        def get_consumo_12m(self, uc_id: str) -> list[dict[str, object]]:
            return [
                {**month, "consumo_kwh": None}
                for month in super().get_consumo_12m(uc_id)
            ]

        def get_faturas_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            return 0, []

        def get_leituras_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            return 0, []

        def get_interrupcoes_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            return 0, []

        def get_chamados_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            return 0, []

    app.dependency_overrides[get_uc_repository] = lambda: nullcontext(EmptyGold())

    response = client.get("/api/uc/UC123456/360")

    assert response.status_code == 200
    body = response.json()
    assert body["medidor_atual"] is None
    assert body["geracao_distribuida"]["possui_gd"] is False
    assert body["faturas_em_aberto"] == []
    assert body["resumo_faturas_em_aberto"] == {"quantidade": 0, "valor_total": None}
    assert len(body["consumo_12m"]) == 12
    assert body["consumo_12m"][0]["consumo_kwh"] is None
    assert all(
        part["total"] == 0 and part["itens"] == []
        for part in body["historicos"].values()
    )


def test_visao_360_http_indisponibilidade_gold_503(
    http_gold: tuple[TestClient, GoldFake],
) -> None:
    client, _ = http_gold

    class FailingGold(GoldFake):
        def get_cadastro(self, uc_id: str) -> None:
            raise GoldUnavailableError("Segredo de conexão")

    app.dependency_overrides[get_uc_repository] = lambda: nullcontext(FailingGold())

    response = client.get("/api/uc/UC123456/360")

    assert response.status_code == 503
    assert response.json() == {"detail": "Gold indisponível"}
    assert "Segredo" not in response.text


def test_visao_360_http_falha_de_historico_nao_entrega_resposta_parcial(
    http_gold: tuple[TestClient, GoldFake],
) -> None:
    client, _ = http_gold

    class FailingHistoryGold(GoldFake):
        def get_chamados_page(self, uc_id: str, limite: int, offset: int) -> None:
            raise GoldUnavailableError("Falha após outras consultas")

    app.dependency_overrides[get_uc_repository] = lambda: nullcontext(
        FailingHistoryGold()
    )

    response = client.get("/api/uc/UC123456/360")

    assert response.status_code == 503
    assert response.json() == {"detail": "Gold indisponível"}
    assert "Maria Exemplo" not in response.text


def test_visao_360_http_libera_contexto_apos_resposta(
    http_gold: tuple[TestClient, GoldFake],
) -> None:
    client, gold = http_gold

    class TrackedContext:
        closed = False

        def __enter__(self) -> GoldFake:
            return gold

        def __exit__(self, *args: object) -> None:
            self.closed = True

    context = TrackedContext()
    app.dependency_overrides[get_uc_repository] = lambda: context

    response = client.get("/api/uc/UC123456/360")

    assert response.status_code == 200
    assert context.closed is True


def test_visao_360_http_preserva_total_zero_explicito(
    http_gold: tuple[TestClient, GoldFake],
) -> None:
    client, _ = http_gold

    class ZeroInvoiceGold(GoldFake):
        def get_faturas_em_aberto(self, uc_id: str) -> list[dict[str, object]]:
            item = super().get_faturas_em_aberto(uc_id)[0]
            return [{**item, "receita_faturada": 0.0}]

        def get_resumo_faturas_em_aberto(self, uc_id: str) -> tuple[int, float]:
            return 1, 0.0

    app.dependency_overrides[get_uc_repository] = lambda: nullcontext(ZeroInvoiceGold())

    response = client.get("/api/uc/UC123456/360")

    assert response.status_code == 200
    assert response.json()["resumo_faturas_em_aberto"] == {
        "quantidade": 1,
        "valor_total": 0.0,
    }


def test_visao_360_http_falha_de_conexao_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.controllers import uc as uc_controller

    class FailingConnection:
        def __enter__(self) -> None:
            raise OperationalError("SELECT secret", {}, Exception("offline"))

        def __exit__(self, *args: object) -> None:
            pass

    monkeypatch.setattr(uc_controller, "get_connection", lambda: FailingConnection())

    response = TestClient(app).get("/api/uc/UC123456/360")

    assert response.status_code == 503
    assert response.json() == {"detail": "Gold indisponível"}
    assert "secret" not in response.text
    assert TestClient(app).get("/api/health").status_code == 200


def test_visao_360_http_erro_sql_inesperado_nao_vira_404(
    http_gold: tuple[TestClient, GoldFake],
) -> None:
    _, _ = http_gold

    class BadSqlGold(GoldFake):
        def get_cadastro(self, uc_id: str) -> None:
            raise ProgrammingError("SELECT sensitive", {}, Exception("bad SQL"))

    app.dependency_overrides[get_uc_repository] = lambda: nullcontext(BadSqlGold())

    response = TestClient(app, raise_server_exceptions=False).get(
        "/api/uc/UC123456/360"
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno"}
    assert "sensitive" not in response.text


def test_visao_360_http_openapi_e_prefixo(
    http_gold: tuple[TestClient, GoldFake],
) -> None:
    client, _ = http_gold
    openapi = client.get("/api/openapi.json").json()
    paths = openapi["paths"]

    assert "/api/uc/{uc_id}/360" in paths
    assert "/uc/{uc_id}/360" not in paths
    assert "/api/api/uc/{uc_id}/360" not in paths
    assert "/api/health" in paths
    parameters = paths["/api/uc/{uc_id}/360"]["get"]["parameters"]
    assert {parameter["name"] for parameter in parameters} == {
        "uc_id",
        "pagina_faturas",
        "pagina_interrupcoes",
        "pagina_chamados",
        "pagina_leituras",
        "limite",
    }
    assert set(openapi["components"]["schemas"]["UC360Response"]["required"]) == {
        "uc",
        "medidor_atual",
        "geracao_distribuida",
        "faturas_em_aberto",
        "resumo_faturas_em_aberto",
        "consumo_12m",
        "historicos",
    }
    responses = paths["/api/uc/{uc_id}/360"]["get"]["responses"]
    assert responses["404"]["content"]["application/json"]["example"] == {
        "detail": "Unidade consumidora não encontrada"
    }
    assert responses["503"]["content"]["application/json"]["example"] == {
        "detail": "Gold indisponível"
    }
    assert client.get("/api/health").json() == {"status": "ok"}


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
@pytest.mark.parametrize(
    ("page_parameter", "history", "table"),
    [
        ("pagina_faturas", "faturas", "fact_faturamento"),
        ("pagina_leituras", "leituras", "fact_leituras"),
        ("pagina_interrupcoes", "interrupcoes", "fact_ocorrencias"),
        ("pagina_chamados", "chamados", "fact_atendimentos"),
    ],
)
def test_visao_360_http_pagina_extrema_preserva_total(
    page_parameter: str, history: str, table: str
) -> None:
    from sqlalchemy import text

    from app.core.database import get_connection

    with get_connection() as connection:
        uc_id = connection.execute(
            text(f"SELECT id_uc FROM {table} LIMIT 1")
        ).scalar_one()
        total = connection.execute(
            text(f"SELECT count(*) FROM {table} WHERE id_uc = :uc_id"),
            {"uc_id": uc_id},
        ).scalar_one()

    page = 10**18
    response = TestClient(app).get(
        f"/api/uc/{uc_id}/360", params={page_parameter: page}
    )

    assert response.status_code == 200
    assert response.json()["historicos"][history] == {
        "pagina": page,
        "limite": 20,
        "total": total,
        "itens": [],
    }


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_visao_360_http_corresponde_a_gold_local_sem_duplicar_fatos() -> None:
    from sqlalchemy import text

    from app.core.database import get_connection

    with get_connection() as connection:
        uc_id = connection.execute(
            text("SELECT id_uc FROM fact_ocorrencias LIMIT 1")
        ).scalar_one()
        cadastro = (
            connection.execute(
                text(
                    "SELECT nome_titular, logradouro, bairro, municipio, classe, "
                    "id_medidor_atual, possui_gd, potencia_gd_kwp "
                    "FROM dim_unidade_consumidora WHERE id_uc = :uc_id"
                ),
                {"uc_id": uc_id},
            )
            .mappings()
            .one()
        )
        resumo = (
            connection.execute(
                text(
                    "SELECT count(*) AS quantidade, sum(receita_faturada) AS valor_total "
                    "FROM fact_faturamento WHERE id_uc = :uc_id "
                    "AND status_pagamento IN ('PENDENTE', 'ATRASADA')"
                ),
                {"uc_id": uc_id},
            )
            .mappings()
            .one()
        )
        counts = {
            name: connection.execute(
                text(f"SELECT count(*) FROM {table} WHERE id_uc = :uc_id"),
                {"uc_id": uc_id},
            ).scalar_one()
            for name, table in (
                ("faturas", "fact_faturamento"),
                ("interrupcoes", "fact_ocorrencias"),
                ("chamados", "fact_atendimentos"),
                ("leituras", "fact_leituras"),
            )
        }
        expected_faturas = (
            connection.execute(
                text(
                    "SELECT id_fatura FROM fact_faturamento WHERE id_uc = :uc_id "
                    "ORDER BY competencia DESC, id_fatura DESC LIMIT 2 OFFSET 2"
                ),
                {"uc_id": uc_id},
            )
            .scalars()
            .all()
        )
        expected_interrupcoes = (
            connection.execute(
                text(
                    "SELECT id_ocorrencia FROM fact_ocorrencias WHERE id_uc = :uc_id "
                    "ORDER BY data_abertura DESC, id_ocorrencia DESC LIMIT 2 OFFSET 0"
                ),
                {"uc_id": uc_id},
            )
            .scalars()
            .all()
        )
        expected_chamados = (
            connection.execute(
                text(
                    "SELECT protocolo FROM fact_atendimentos WHERE id_uc = :uc_id "
                    "ORDER BY data_abertura DESC, protocolo DESC LIMIT 2 OFFSET 0"
                ),
                {"uc_id": uc_id},
            )
            .scalars()
            .all()
        )
        expected_leituras = (
            connection.execute(
                text(
                    "SELECT id_leitura FROM fact_leituras WHERE id_uc = :uc_id "
                    "ORDER BY competencia DESC, id_leitura DESC LIMIT 2 OFFSET 0"
                ),
                {"uc_id": uc_id},
            )
            .scalars()
            .all()
        )
        last_month = connection.execute(
            text(
                "SELECT mes_referencia FROM dim_competencia "
                "ORDER BY competencia DESC LIMIT 1"
            )
        ).scalar_one()
        last_reading = (
            connection.execute(
                text(
                    "SELECT consumo_kwh, consumo_ano_anterior_kwh, "
                    "variacao_ano_anterior_pct FROM fact_leituras "
                    "WHERE id_uc = :uc_id AND mes_referencia = :mes_referencia"
                ),
                {"uc_id": uc_id, "mes_referencia": last_month},
            )
            .mappings()
            .one_or_none()
        )

    response = TestClient(app).get(f"/api/uc/{uc_id}/360?limite=2&pagina_faturas=2")

    assert response.status_code == 200
    body = response.json()
    assert body["uc"]["id_uc"] == uc_id
    assert all(
        body["uc"][field] == cadastro[field]
        for field in ("nome_titular", "logradouro", "bairro", "municipio", "classe")
    )
    assert body["geracao_distribuida"]["possui_gd"] == cadastro["possui_gd"]
    assert body["geracao_distribuida"]["potencia_gd_kwp"] == cadastro["potencia_gd_kwp"]
    assert (body["medidor_atual"] is None) == (cadastro["id_medidor_atual"] is None)
    assert body["resumo_faturas_em_aberto"] == dict(resumo)
    assert len(body["faturas_em_aberto"]) == resumo["quantidade"]
    assert all(
        item["status_pagamento"] in ("PENDENTE", "ATRASADA")
        for item in body["faturas_em_aberto"]
    )
    assert len(body["consumo_12m"]) == 12
    assert body["consumo_12m"][-1]["mes_referencia"] == last_month
    assert all(
        body["consumo_12m"][-1][field]
        == (last_reading[field] if last_reading else None)
        for field in (
            "consumo_kwh",
            "consumo_ano_anterior_kwh",
            "variacao_ano_anterior_pct",
        )
    )
    assert {name: part["total"] for name, part in body["historicos"].items()} == counts
    assert body["historicos"]["faturas"]["pagina"] == 2
    assert [
        item["id_fatura"] for item in body["historicos"]["faturas"]["itens"]
    ] == expected_faturas
    assert [
        item["id_ocorrencia"] for item in body["historicos"]["interrupcoes"]["itens"]
    ] == expected_interrupcoes
    assert [
        item["protocolo"] for item in body["historicos"]["chamados"]["itens"]
    ] == expected_chamados
    assert [
        item["id_leitura"] for item in body["historicos"]["leituras"]["itens"]
    ] == expected_leituras
