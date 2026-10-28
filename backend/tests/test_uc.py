"""Cadastro da UC: comportamento do caso de uso antes da rota HTTP."""

from datetime import date, datetime

import pytest
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.core.config import get_settings
from app.exceptions.uc import (
    GoldUnavailableError,
    InvalidPaginationError,
    InvalidUCIdError,
    UCNotFoundError,
)
from app.repositories.uc import UCRepository
from app.schemas.uc import (
    UCCadastro,
    UCConsumptionReadings,
    UCInvoices,
    UCOperationalHistories,
)
from app.services.uc import (
    get_cadastro_uc,
    get_consumo_e_leituras,
    get_faturas,
    get_interrupcoes_e_chamados,
    get_resumo_faturas_em_aberto,
)


class CadastroGold:
    def __init__(self, row: dict[str, object] | None):
        self.row = row

    def get_cadastro(self, uc_id: str) -> dict[str, object] | None:
        return self.row


def cadastro_gold() -> dict[str, object]:
    return {
        "id_uc": "UC123456",
        "nome_titular": "Maria Silva",
        "logradouro": "Rua Exemplo",
        "numero": "100",
        "bairro": "Boa Viagem",
        "municipio": "Recife",
        "uf": "PE",
        "classe": "RESIDENCIAL",
        "id_medidor_atual": "MED123456",
        "tipo_medidor_atual": "SMART",
        "modelo_medidor_atual": "SM-4100",
        "data_instalacao_medidor_atual": date(2025, 9, 15),
        "possui_gd": True,
        "data_conexao_gd": date(2024, 5, 1),
        "potencia_gd_kwp": 4.5,
        "modalidade_gd": "GERACAO NA PROPRIA UC",
    }


def test_cadastro_preserva_valores_gold_e_campos_contratados() -> None:
    row = cadastro_gold()
    row["cpf_cnpj_mascarado"] = "***1234"

    result = UCCadastro.model_validate(get_cadastro_uc("UC123456", CadastroGold(row)))

    assert result.model_dump(mode="json") == {
        "uc": {
            "id_uc": "UC123456",
            "nome_titular": "Maria Silva",
            "logradouro": "Rua Exemplo",
            "numero": "100",
            "bairro": "Boa Viagem",
            "municipio": "Recife",
            "uf": "PE",
            "classe": "RESIDENCIAL",
        },
        "medidor_atual": {
            "id_medidor_atual": "MED123456",
            "tipo_medidor_atual": "SMART",
            "modelo_medidor_atual": "SM-4100",
            "data_instalacao_medidor_atual": "2025-09-15",
        },
        "geracao_distribuida": {
            "possui_gd": True,
            "data_conexao_gd": "2024-05-01",
            "potencia_gd_kwp": 4.5,
            "modalidade_gd": "GERACAO NA PROPRIA UC",
        },
    }


@pytest.mark.parametrize(
    "uc_id",
    ["", "123456", "UC12345", "UC1234567", "uc123456", "UC12345x", "UC123456' OR true"],
)
def test_id_malformado_nao_consulta_gold(uc_id: str) -> None:
    class UnexpectedGold:
        def get_cadastro(self, uc_id: str) -> None:
            pytest.fail("ID malformado não pode consultar a Gold")

    with pytest.raises(InvalidUCIdError):
        get_cadastro_uc(uc_id, UnexpectedGold())


def test_uc_inexistente_e_diferente_de_falha_do_banco() -> None:
    with pytest.raises(UCNotFoundError):
        get_cadastro_uc("UC999999", CadastroGold(None))


def test_medidor_ausente_e_gd_ausente_sao_dados_normais() -> None:
    row = cadastro_gold()
    row.update(
        id_medidor_atual=None,
        tipo_medidor_atual=None,
        modelo_medidor_atual=None,
        data_instalacao_medidor_atual=None,
        possui_gd=False,
        data_conexao_gd=None,
        potencia_gd_kwp=None,
        modalidade_gd=None,
        nome_titular=None,
    )

    result = UCCadastro.model_validate(get_cadastro_uc("UC123456", CadastroGold(row)))

    assert result.medidor_atual is None
    assert result.geracao_distribuida.possui_gd is False
    assert result.geracao_distribuida.potencia_gd_kwp is None
    assert result.uc.nome_titular is None


def test_medidor_parcial_e_gd_nula_preservam_gold() -> None:
    row = cadastro_gold()
    row.update(modelo_medidor_atual=None, possui_gd=None, potencia_gd_kwp=None)

    result = UCCadastro.model_validate(get_cadastro_uc("UC123456", CadastroGold(row)))

    assert result.medidor_atual is not None
    assert result.medidor_atual.modelo_medidor_atual is None
    assert result.geracao_distribuida.possui_gd is None
    assert result.geracao_distribuida.potencia_gd_kwp is None


def test_falha_gold_permanece_distinta_de_uc_inexistente() -> None:
    class FailingGold:
        def get_cadastro(self, uc_id: str) -> None:
            raise GoldUnavailableError("Gold indisponível")

    with pytest.raises(GoldUnavailableError):
        get_cadastro_uc("UC123456", FailingGold())


def test_repository_distingue_indisponibilidade_de_erro_sql() -> None:
    class FailingConnection:
        def __init__(self, error: Exception):
            self.error = error

        def execute(self, statement: object, parameters: object) -> None:
            raise self.error

    operational = OperationalError("SELECT", {}, Exception("offline"))
    with pytest.raises(GoldUnavailableError):
        UCRepository(FailingConnection(operational)).get_cadastro("UC123456")

    programming = ProgrammingError("SELECT", {}, Exception("coluna inválida"))
    with pytest.raises(ProgrammingError):
        UCRepository(FailingConnection(programming)).get_cadastro("UC123456")


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_cadastro_gold_real_e_consulta_exata_sem_duplicacao() -> None:
    from sqlalchemy import text

    from app.core.database import get_connection

    with get_connection() as connection:
        uc_id = connection.execute(
            text("SELECT id_uc FROM dim_unidade_consumidora ORDER BY id_uc LIMIT 1")
        ).scalar_one()
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM dim_unidade_consumidora WHERE id_uc = :uc_id"
                ),
                {"uc_id": uc_id},
            ).scalar_one()
            == 1
        )

        cadastro = get_cadastro_uc(uc_id, UCRepository(connection))
        source = (
            connection.execute(
                text(
                    "SELECT nome_titular, classe, id_medidor_atual, possui_gd, "
                    "potencia_gd_kwp FROM dim_unidade_consumidora WHERE id_uc = :uc_id"
                ),
                {"uc_id": uc_id},
            )
            .mappings()
            .one()
        )

        assert cadastro["uc"]["id_uc"] == uc_id
        assert cadastro["uc"]["nome_titular"] == source["nome_titular"]
        assert cadastro["uc"]["classe"] == source["classe"]
        if source["id_medidor_atual"] is None:
            assert cadastro["medidor_atual"] is None
        else:
            assert (
                cadastro["medidor_atual"]["id_medidor_atual"]
                == source["id_medidor_atual"]
            )
        assert cadastro["geracao_distribuida"]["possui_gd"] == source["possui_gd"]
        assert (
            cadastro["geracao_distribuida"]["potencia_gd_kwp"]
            == source["potencia_gd_kwp"]
        )
        assert UCRepository(connection).get_cadastro("UC123456' OR true --") is None


def test_consumo_e_leituras_preservam_valores_publicados_pela_gold() -> None:
    class LeiturasGold:
        def get_consumo_12m(self, uc_id: str) -> list[dict[str, object]]:
            return [
                {
                    "mes_referencia": f"2025-{month:02d}"
                    if month >= 7
                    else f"2026-{month:02d}",
                    "consumo_kwh": 123.4 if month == 6 else None,
                    "consumo_ano_anterior_kwh": 98.1 if month == 6 else None,
                    "variacao_ano_anterior_pct": 25.79 if month == 6 else None,
                }
                for month in (*range(7, 13), *range(1, 7))
            ]

        def get_leituras_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            return 1, [
                {
                    "id_leitura": "LEI123",
                    "id_medidor": "MED123",
                    "mes_referencia": "2026-06",
                    "data_leitura": date(2026, 6, 25),
                    "leitura_anterior": 100.0,
                    "leitura_atual": 900.0,
                    "consumo_kwh": 123.4,
                    "consumo_ano_anterior_kwh": 98.1,
                    "variacao_ano_anterior_pct": 25.79,
                    "tipo_leitura": "ESTIMADA",
                    "status_qualidade_leitura": "TROCA_DE_MEDIDOR",
                    "consumo_imputado": True,
                }
            ]

    result = get_consumo_e_leituras("UC123456", 1, 20, LeiturasGold())

    assert len(result["consumo_12m"]) == 12
    assert result["consumo_12m"][0]["mes_referencia"] == "2025-07"
    assert result["consumo_12m"][-1] == {
        "mes_referencia": "2026-06",
        "consumo_kwh": 123.4,
        "consumo_ano_anterior_kwh": 98.1,
        "variacao_ano_anterior_pct": 25.79,
    }
    assert result["historicos"]["leituras"]["itens"][0]["consumo_kwh"] == 123.4
    assert result["historicos"]["leituras"]["itens"][0]["consumo_imputado"] is True
    serialized = UCConsumptionReadings.model_validate(result).model_dump(mode="json")
    assert serialized["historicos"]["leituras"]["itens"][0] == {
        "id_leitura": "LEI123",
        "id_medidor": "MED123",
        "mes_referencia": "2026-06",
        "data_leitura": "2026-06-25",
        "leitura_anterior": 100.0,
        "leitura_atual": 900.0,
        "consumo_kwh": 123.4,
        "consumo_ano_anterior_kwh": 98.1,
        "variacao_ano_anterior_pct": 25.79,
        "tipo_leitura": "ESTIMADA",
        "status_qualidade_leitura": "TROCA_DE_MEDIDOR",
        "consumo_imputado": True,
    }


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_janela_de_consumo_usa_calendario_e_valores_gold() -> None:
    from sqlalchemy import text

    from app.core.database import get_connection

    with get_connection() as connection:
        uc_id = connection.execute(
            text("SELECT id_uc FROM dim_unidade_consumidora ORDER BY id_uc LIMIT 1")
        ).scalar_one()
        months = (
            connection.execute(
                text(
                    "SELECT competencia, mes_referencia FROM dim_competencia "
                    "ORDER BY competencia DESC LIMIT 12"
                )
            )
            .mappings()
            .all()
        )

        result = UCRepository(connection).get_consumo_12m(uc_id)

        assert len(result) == 12
        assert [row["mes_referencia"] for row in result] == [
            month["mes_referencia"] for month in reversed(months)
        ]
        last_gold = (
            connection.execute(
                text(
                    "SELECT consumo_kwh, consumo_ano_anterior_kwh, "
                    "variacao_ano_anterior_pct FROM fact_leituras "
                    "WHERE id_uc = :uc_id AND competencia = :competencia"
                ),
                {"uc_id": uc_id, "competencia": months[0]["competencia"]},
            )
            .mappings()
            .one_or_none()
        )
        assert result[-1]["consumo_kwh"] == (
            last_gold["consumo_kwh"] if last_gold else None
        )
        assert result[-1]["consumo_ano_anterior_kwh"] == (
            last_gold["consumo_ano_anterior_kwh"] if last_gold else None
        )
        assert result[-1]["variacao_ano_anterior_pct"] == (
            last_gold["variacao_ano_anterior_pct"] if last_gold else None
        )


@pytest.mark.parametrize(
    ("pagina", "limite"),
    [(0, 20), (-1, 20), (1, 0), (1, 51), (True, 20), (1, False)],
)
def test_paginacao_invalida_nao_consulta_gold(pagina: int, limite: int) -> None:
    class UnexpectedGold:
        def get_consumo_12m(self, uc_id: str) -> None:
            pytest.fail("Paginação inválida não pode consultar a Gold")

        def get_leituras_page(self, uc_id: str, limite: int, offset: int) -> None:
            pytest.fail("Paginação inválida não pode consultar a Gold")

    with pytest.raises(InvalidPaginationError):
        get_consumo_e_leituras("UC123456", pagina, limite, UnexpectedGold())


def test_uc_sem_leituras_mantem_calendario_e_historico_vazio() -> None:
    class EmptyGold:
        def get_consumo_12m(self, uc_id: str) -> list[dict[str, object]]:
            return [
                {
                    "mes_referencia": "2026-06",
                    "consumo_kwh": None,
                    "consumo_ano_anterior_kwh": None,
                    "variacao_ano_anterior_pct": None,
                }
            ] * 12

        def get_leituras_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            return 0, []

    result = get_consumo_e_leituras("UC123456", 2, 20, EmptyGold())

    assert len(result["consumo_12m"]) == 12
    assert all(row["consumo_kwh"] is None for row in result["consumo_12m"])
    assert result["historicos"]["leituras"] == {
        "pagina": 2,
        "limite": 20,
        "total": 0,
        "itens": [],
    }


def test_pagina_alem_do_total_preserva_total_e_nao_altera_grafico() -> None:
    class GoldWithOneReading:
        def get_consumo_12m(self, uc_id: str) -> list[dict[str, object]]:
            return [
                {
                    "mes_referencia": "2026-06",
                    "consumo_kwh": 0.0,
                    "consumo_ano_anterior_kwh": None,
                    "variacao_ano_anterior_pct": None,
                }
            ]

        def get_leituras_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            assert limite == 20 and offset == 20
            return 1, []

    result = get_consumo_e_leituras("UC123456", 2, 20, GoldWithOneReading())

    assert result["consumo_12m"][0]["consumo_kwh"] == 0.0
    assert result["historicos"]["leituras"] == {
        "pagina": 2,
        "limite": 20,
        "total": 1,
        "itens": [],
    }


def test_falha_em_leituras_ou_calendario_nao_vira_historico_vazio() -> None:
    class FailingReadings:
        def get_leituras_page(self, uc_id: str, limite: int, offset: int) -> None:
            raise GoldUnavailableError("Gold indisponível")

    class FailingCalendar:
        def get_leituras_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            return 0, []

        def get_consumo_12m(self, uc_id: str) -> None:
            raise GoldUnavailableError("Gold indisponível")

    with pytest.raises(GoldUnavailableError):
        get_consumo_e_leituras("UC123456", 1, 20, FailingReadings())
    with pytest.raises(GoldUnavailableError):
        get_consumo_e_leituras("UC123456", 1, 20, FailingCalendar())


def test_consultas_de_leituras_traduzem_indisponibilidade_gold() -> None:
    class FailingConnection:
        def execute(self, statement: object, parameters: object) -> None:
            raise OperationalError("SELECT", {}, Exception("offline"))

    repository = UCRepository(FailingConnection())

    with pytest.raises(GoldUnavailableError):
        repository.get_consumo_12m("UC123456")
    with pytest.raises(GoldUnavailableError):
        repository.get_leituras_page("UC123456", 20, 0)


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_historico_leituras_gold_paginado_e_sem_duplicacao() -> None:
    from sqlalchemy import text

    from app.core.database import get_connection

    with get_connection() as connection:
        uc_id = connection.execute(
            text("SELECT id_uc FROM dim_unidade_consumidora ORDER BY id_uc LIMIT 1")
        ).scalar_one()
        total_gold = connection.execute(
            text("SELECT count(*) FROM fact_leituras WHERE id_uc = :uc_id"),
            {"uc_id": uc_id},
        ).scalar_one()
        expected = (
            connection.execute(
                text(
                    "SELECT id_leitura, consumo_kwh, consumo_imputado "
                    "FROM fact_leituras WHERE id_uc = :uc_id "
                    "ORDER BY competencia DESC, id_leitura DESC LIMIT 2 OFFSET 2"
                ),
                {"uc_id": uc_id},
            )
            .mappings()
            .all()
        )

        repository = UCRepository(connection)
        total, itens = repository.get_leituras_page(uc_id, 2, 2)
        total_beyond, beyond = repository.get_leituras_page(uc_id, 2, total_gold)
        empty_total, empty = repository.get_leituras_page("' OR true --", 2, 0)

        assert total == total_gold
        assert [item["id_leitura"] for item in itens] == [
            row["id_leitura"] for row in expected
        ]
        assert [item["consumo_kwh"] for item in itens] == [
            row["consumo_kwh"] for row in expected
        ]
        assert [item["consumo_imputado"] for item in itens] == [
            row["consumo_imputado"] for row in expected
        ]
        assert len({item["id_leitura"] for item in itens}) == len(itens)
        assert total_beyond == total_gold and beyond == []
        assert empty_total == 0 and empty == []


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_consumo_imputado_real_preserva_valor_gold_e_sinalizador() -> None:
    from sqlalchemy import text

    from app.core.database import get_connection

    with get_connection() as connection:
        source = (
            connection.execute(
                text(
                    "SELECT id_uc, id_leitura, mes_referencia, consumo_kwh "
                    "FROM fact_leituras WHERE consumo_imputado = true LIMIT 1"
                )
            )
            .mappings()
            .one()
        )
        repository = UCRepository(connection)
        chart = repository.get_consumo_12m(source["id_uc"])
        _, readings = repository.get_leituras_page(source["id_uc"], 50, 0)
        no_readings = repository.get_consumo_12m("' OR true --")

        matching_month = [
            month
            for month in chart
            if month["mes_referencia"] == source["mes_referencia"]
        ]
        matching_reading = [
            reading
            for reading in readings
            if reading["id_leitura"] == source["id_leitura"]
        ]
        assert len(matching_month) == 1
        assert matching_month[0]["consumo_kwh"] == source["consumo_kwh"]
        assert len(matching_reading) == 1
        assert matching_reading[0]["consumo_kwh"] == source["consumo_kwh"]
        assert matching_reading[0]["consumo_imputado"] is True
        assert len(no_readings) == 12
        assert all(month["consumo_kwh"] is None for month in no_readings)


def test_faturas_em_aberto_e_historico_preservam_gold() -> None:
    class FaturasGold:
        def get_faturas_em_aberto(self, uc_id: str) -> list[dict[str, object]]:
            return [
                {
                    "id_fatura": "FT001",
                    "mes_referencia": "2026-05",
                    "data_vencimento": date(2026, 6, 12),
                    "receita_faturada": 185.501,
                    "status_pagamento": "ATRASADA",
                }
            ]

        def get_faturas_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            return 1, [
                {
                    "id_fatura": "FT001",
                    "mes_referencia": "2026-05",
                    "consumo_kwh": 205.0,
                    "bandeira_tarifaria": "VERDE",
                    "receita_faturada": 185.501,
                    "data_vencimento": date(2026, 6, 12),
                    "status_pagamento": "ATRASADA",
                    "data_emissao": date(2026, 5, 31),
                    "data_pagamento": None,
                    "dias_atraso": 19,
                }
            ]

    result = UCInvoices.model_validate(
        get_faturas("UC123456", 1, 20, FaturasGold())
    ).model_dump(mode="json")

    assert result == {
        "faturas_em_aberto": [
            {
                "id_fatura": "FT001",
                "mes_referencia": "2026-05",
                "data_vencimento": "2026-06-12",
                "receita_faturada": 185.501,
                "status_pagamento": "ATRASADA",
            }
        ],
        "historicos": {
            "faturas": {
                "pagina": 1,
                "limite": 20,
                "total": 1,
                "itens": [
                    {
                        "id_fatura": "FT001",
                        "mes_referencia": "2026-05",
                        "consumo_kwh": 205.0,
                        "bandeira_tarifaria": "VERDE",
                        "receita_faturada": 185.501,
                        "data_vencimento": "2026-06-12",
                        "status_pagamento": "ATRASADA",
                        "data_emissao": "2026-05-31",
                        "data_pagamento": None,
                        "dias_atraso": 19,
                    }
                ],
            }
        },
    }


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_faturas_em_aberto_reais_usam_status_e_ordem_gold() -> None:
    from sqlalchemy import text

    from app.core.database import get_connection

    with get_connection() as connection:
        uc_id = connection.execute(
            text(
                "SELECT id_uc FROM fact_faturamento "
                "WHERE status_pagamento IN ('PENDENTE', 'ATRASADA') LIMIT 1"
            )
        ).scalar_one()
        expected = (
            connection.execute(
                text(
                    "SELECT id_fatura, mes_referencia, data_vencimento, "
                    "receita_faturada, status_pagamento FROM fact_faturamento "
                    "WHERE id_uc = :uc_id AND status_pagamento IN ('PENDENTE', 'ATRASADA') "
                    "ORDER BY data_vencimento, id_fatura"
                ),
                {"uc_id": uc_id},
            )
            .mappings()
            .all()
        )

        result = UCRepository(connection).get_faturas_em_aberto(uc_id)

        assert result == [dict(row) for row in expected]
        assert all(
            row["status_pagamento"] in ("PENDENTE", "ATRASADA") for row in result
        )
        assert UCRepository(connection).get_faturas_em_aberto("' OR true --") == []


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_historico_de_faturas_gold_paginado_e_sem_duplicacao() -> None:
    from sqlalchemy import text

    from app.core.database import get_connection

    with get_connection() as connection:
        uc_id = connection.execute(
            text("SELECT id_uc FROM fact_faturamento LIMIT 1")
        ).scalar_one()
        total_gold = connection.execute(
            text("SELECT count(*) FROM fact_faturamento WHERE id_uc = :uc_id"),
            {"uc_id": uc_id},
        ).scalar_one()
        expected = (
            connection.execute(
                text(
                    "SELECT id_fatura, mes_referencia, consumo_kwh, bandeira_tarifaria, "
                    "receita_faturada, data_vencimento, status_pagamento, data_emissao, "
                    "data_pagamento, dias_atraso FROM fact_faturamento "
                    "WHERE id_uc = :uc_id "
                    "ORDER BY competencia DESC, id_fatura DESC LIMIT 2 OFFSET 2"
                ),
                {"uc_id": uc_id},
            )
            .mappings()
            .all()
        )

        repository = UCRepository(connection)
        total, itens = repository.get_faturas_page(uc_id, 2, 2)
        total_beyond, beyond = repository.get_faturas_page(uc_id, 2, total_gold)
        empty_total, empty = repository.get_faturas_page("' OR true --", 2, 0)

        assert total == total_gold
        assert itens == [dict(row) for row in expected]
        assert len({item["id_fatura"] for item in itens}) == len(itens)
        assert total_beyond == total_gold and beyond == []
        assert empty_total == 0 and empty == []


def test_uc_sem_faturas_ou_sem_abertas_preserva_ausencias_e_zero() -> None:
    class EmptyInvoices:
        def get_faturas_em_aberto(self, uc_id: str) -> list[dict[str, object]]:
            return []

        def get_faturas_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            return 0, []

    empty = UCInvoices.model_validate(get_faturas("UC123456", 1, 20, EmptyInvoices()))
    assert empty.faturas_em_aberto == []
    assert empty.historicos.faturas.total == 0
    assert empty.historicos.faturas.itens == []

    class PaidOnly:
        def get_faturas_em_aberto(self, uc_id: str) -> list[dict[str, object]]:
            return []

        def get_faturas_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            return 1, [
                {
                    "id_fatura": "FT002",
                    "mes_referencia": "2026-04",
                    "consumo_kwh": None,
                    "bandeira_tarifaria": "VERDE",
                    "receita_faturada": 0.0,
                    "data_vencimento": None,
                    "status_pagamento": "PAGA",
                    "data_emissao": None,
                    "data_pagamento": None,
                    "dias_atraso": 0,
                }
            ]

    paid = UCInvoices.model_validate(get_faturas("UC123456", 1, 20, PaidOnly()))
    assert paid.faturas_em_aberto == []
    assert paid.historicos.faturas.total == 1
    assert paid.historicos.faturas.itens[0].receita_faturada == 0.0
    assert paid.historicos.faturas.itens[0].consumo_kwh is None
    assert paid.historicos.faturas.itens[0].data_vencimento is None


def test_fatura_aberta_preserva_status_e_valor_nulo_da_gold() -> None:
    class NullAmountGold:
        def get_faturas_em_aberto(self, uc_id: str) -> list[dict[str, object]]:
            return [
                {
                    "id_fatura": "FT003",
                    "mes_referencia": "2026-06",
                    "data_vencimento": date(2026, 7, 12),
                    "receita_faturada": None,
                    "status_pagamento": "PENDENTE",
                }
            ]

        def get_faturas_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            return 1, []

    result = UCInvoices.model_validate(get_faturas("UC123456", 2, 20, NullAmountGold()))

    assert result.faturas_em_aberto[0].receita_faturada is None
    assert result.faturas_em_aberto[0].status_pagamento == "PENDENTE"
    assert result.historicos.faturas.total == 1
    assert result.historicos.faturas.itens == []


def test_pagina_de_faturas_alem_do_total_preserva_contagem() -> None:
    class OneInvoice:
        def get_faturas_em_aberto(self, uc_id: str) -> list[dict[str, object]]:
            return []

        def get_faturas_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            assert limite == 20 and offset == 20
            return 1, []

    result = get_faturas("UC123456", 2, 20, OneInvoice())

    assert result["historicos"]["faturas"] == {
        "pagina": 2,
        "limite": 20,
        "total": 1,
        "itens": [],
    }


def test_paginacao_invalida_de_faturas_nao_consulta_gold() -> None:
    class UnexpectedGold:
        def get_faturas_em_aberto(self, uc_id: str) -> None:
            pytest.fail("Paginação inválida não pode consultar a Gold")

    with pytest.raises(InvalidPaginationError):
        get_faturas("UC123456", 0, 20, UnexpectedGold())
    with pytest.raises(InvalidPaginationError):
        get_faturas("UC123456", 1, 51, UnexpectedGold())


def test_falha_faturas_nao_vira_lista_vazia() -> None:
    class FailingOpenInvoices:
        def get_faturas_em_aberto(self, uc_id: str) -> None:
            raise GoldUnavailableError("Gold indisponível")

    class FailingHistory:
        def get_faturas_em_aberto(self, uc_id: str) -> list[dict[str, object]]:
            return []

        def get_faturas_page(self, uc_id: str, limite: int, offset: int) -> None:
            raise GoldUnavailableError("Gold indisponível")

    with pytest.raises(GoldUnavailableError):
        get_faturas("UC123456", 1, 20, FailingOpenInvoices())
    with pytest.raises(GoldUnavailableError):
        get_faturas("UC123456", 1, 20, FailingHistory())


def test_consultas_de_faturas_traduzem_indisponibilidade_gold() -> None:
    class FailingConnection:
        def execute(self, statement: object, parameters: object) -> None:
            raise OperationalError("SELECT", {}, Exception("offline"))

    repository = UCRepository(FailingConnection())

    with pytest.raises(GoldUnavailableError):
        repository.get_faturas_em_aberto("UC123456")
    with pytest.raises(GoldUnavailableError):
        repository.get_faturas_page("UC123456", 20, 0)
    with pytest.raises(GoldUnavailableError):
        repository.get_resumo_faturas_em_aberto("UC123456")


@pytest.mark.parametrize(
    ("gold_value", "expected"),
    [
        ((0, None), {"quantidade": 0, "valor_total": None}),
        ((1, 0.0), {"quantidade": 1, "valor_total": 0.0}),
        ((2, 185.501), {"quantidade": 2, "valor_total": 185.501}),
    ],
)
def test_resumo_faturas_em_aberto_distingue_ausencia_e_zero(
    gold_value: tuple[int, float | None], expected: dict[str, object]
) -> None:
    class SummaryGold:
        def get_resumo_faturas_em_aberto(self, uc_id: str) -> tuple[int, float | None]:
            return gold_value

    assert get_resumo_faturas_em_aberto("UC123456", SummaryGold()) == expected


def test_falha_do_resumo_nao_vira_zero() -> None:
    class FailingSummary:
        def get_resumo_faturas_em_aberto(self, uc_id: str) -> None:
            raise GoldUnavailableError("Gold indisponível")

    with pytest.raises(GoldUnavailableError):
        get_resumo_faturas_em_aberto("UC123456", FailingSummary())


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_resumo_faturas_em_aberto_corresponde_a_gold() -> None:
    from sqlalchemy import text

    from app.core.database import get_connection

    with get_connection() as connection:
        uc_id = connection.execute(
            text(
                "SELECT id_uc FROM fact_faturamento "
                "WHERE status_pagamento IN ('PENDENTE', 'ATRASADA') LIMIT 1"
            )
        ).scalar_one()
        expected = (
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

        repository = UCRepository(connection)
        quantidade, valor_total = repository.get_resumo_faturas_em_aberto(uc_id)
        empty_quantidade, empty_valor = repository.get_resumo_faturas_em_aberto(
            "' OR true --"
        )

        assert quantidade == expected["quantidade"]
        assert quantidade == len(repository.get_faturas_em_aberto(uc_id))
        assert valor_total == expected["valor_total"]
        assert empty_quantidade == 0 and empty_valor is None


def test_interrupcoes_e_chamados_preservam_gold_e_paginas_independentes() -> None:
    class HistoricosGold:
        def get_interrupcoes_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            assert (uc_id, limite, offset) == ("UC123456", 2, 2)
            return 3, [
                {
                    "id_ocorrencia": "OCO-1",
                    "alimentador": "ALM-REC-008",
                    "tipo": "FALTA DE ENERGIA",
                    "causa": "VEGETACAO",
                    "data_abertura": datetime(2026, 6, 2, 10),
                    "data_encerramento": None,
                    "duracao_h": 2.75,
                    "duracao_truncada": True,
                }
            ]

        def get_chamados_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            assert (uc_id, limite, offset) == ("UC123456", 2, 0)
            return 1, [
                {
                    "protocolo": "PROT-1",
                    "assunto": "FATURA",
                    "subassunto": "VALOR ALTO",
                    "canal": "TELEFONE",
                    "data_abertura": datetime(2026, 6, 16, 9),
                    "data_fechamento": None,
                    "status_chamado": "ABERTO",
                    "qtd_tratativas": 0,
                }
            ]

    result = UCOperationalHistories.model_validate(
        get_interrupcoes_e_chamados("UC123456", 2, 1, 2, HistoricosGold())
    ).model_dump(mode="json")

    assert result == {
        "historicos": {
            "interrupcoes": {
                "pagina": 2,
                "limite": 2,
                "total": 3,
                "itens": [
                    {
                        "id_ocorrencia": "OCO-1",
                        "alimentador": "ALM-REC-008",
                        "tipo": "FALTA DE ENERGIA",
                        "causa": "VEGETACAO",
                        "data_abertura": "2026-06-02T10:00:00",
                        "data_encerramento": None,
                        "duracao_h": 2.75,
                        "duracao_truncada": True,
                    }
                ],
            },
            "chamados": {
                "pagina": 1,
                "limite": 2,
                "total": 1,
                "itens": [
                    {
                        "protocolo": "PROT-1",
                        "assunto": "FATURA",
                        "subassunto": "VALOR ALTO",
                        "canal": "TELEFONE",
                        "data_abertura": "2026-06-16T09:00:00",
                        "data_fechamento": None,
                        "status_chamado": "ABERTO",
                        "qtd_tratativas": 0,
                    }
                ],
            },
        }
    }


def test_historicos_operacionais_ausentes_ou_pagina_alem_do_fim() -> None:
    class SparseGold:
        def get_interrupcoes_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            assert offset == 20
            return 1, []

        def get_chamados_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            assert offset == 0
            return 0, []

    result = get_interrupcoes_e_chamados("UC123456", 2, 1, 20, SparseGold())

    assert result == {
        "historicos": {
            "interrupcoes": {"pagina": 2, "limite": 20, "total": 1, "itens": []},
            "chamados": {"pagina": 1, "limite": 20, "total": 0, "itens": []},
        }
    }


@pytest.mark.parametrize(
    ("pagina_interrupcoes", "pagina_chamados", "limite"),
    [(0, 1, 20), (1, 0, 20), (1, 1, 0), (1, 1, 51)],
)
def test_paginacao_operacional_invalida_nao_consulta_gold(
    pagina_interrupcoes: int, pagina_chamados: int, limite: int
) -> None:
    class UnexpectedGold:
        def get_interrupcoes_page(self, *args: object) -> None:
            pytest.fail("Paginação inválida não pode consultar a Gold")

    with pytest.raises(InvalidPaginationError):
        get_interrupcoes_e_chamados(
            "UC123456", pagina_interrupcoes, pagina_chamados, limite, UnexpectedGold()
        )


def test_falha_em_historico_operacional_nao_vira_lista_vazia() -> None:
    class FailingGold:
        def get_interrupcoes_page(
            self, uc_id: str, limite: int, offset: int
        ) -> tuple[int, list[dict[str, object]]]:
            return 0, []

        def get_chamados_page(self, uc_id: str, limite: int, offset: int) -> None:
            raise GoldUnavailableError("Gold indisponível")

    with pytest.raises(GoldUnavailableError):
        get_interrupcoes_e_chamados("UC123456", 1, 1, 20, FailingGold())


def test_consultas_operacionais_traduzem_indisponibilidade_gold() -> None:
    class FailingConnection:
        def execute(self, statement: object, parameters: object) -> None:
            raise OperationalError("SELECT", {}, Exception("offline"))

    repository = UCRepository(FailingConnection())

    with pytest.raises(GoldUnavailableError):
        repository.get_interrupcoes_page("UC123456", 20, 0)
    with pytest.raises(GoldUnavailableError):
        repository.get_chamados_page("UC123456", 20, 0)


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
@pytest.mark.parametrize(
    ("table", "method", "identifier", "fields"),
    [
        (
            "fact_ocorrencias",
            "get_interrupcoes_page",
            "id_ocorrencia",
            (
                "id_ocorrencia, alimentador, tipo, causa, data_abertura, "
                "data_encerramento, duracao_h, duracao_truncada"
            ),
        ),
        (
            "fact_atendimentos",
            "get_chamados_page",
            "protocolo",
            (
                "protocolo, assunto, subassunto, canal, data_abertura, "
                "data_fechamento, status_chamado, qtd_tratativas"
            ),
        ),
    ],
)
def test_historicos_operacionais_gold_isolados_e_ordenados(
    table: str, method: str, identifier: str, fields: str
) -> None:
    from sqlalchemy import text

    from app.core.database import get_connection

    with get_connection() as connection:
        uc_id = connection.execute(
            text(f"SELECT id_uc FROM {table} LIMIT 1")
        ).scalar_one()
        total_gold = connection.execute(
            text(f"SELECT count(*) FROM {table} WHERE id_uc = :uc_id"),
            {"uc_id": uc_id},
        ).scalar_one()
        expected = (
            connection.execute(
                text(
                    f"SELECT {fields} FROM {table} WHERE id_uc = :uc_id "
                    f"ORDER BY data_abertura DESC, {identifier} DESC LIMIT 2 OFFSET 2"
                ),
                {"uc_id": uc_id},
            )
            .mappings()
            .all()
        )
        repository = UCRepository(connection)
        page = getattr(repository, method)

        total, items = page(uc_id, 2, 2)
        beyond_total, beyond_items = page(uc_id, 2, total_gold)
        absent_total, absent_items = page("' OR true --", 2, 0)

        assert total == total_gold
        assert items == [dict(row) for row in expected]
        assert len(items) <= 2
        assert beyond_total == total_gold and beyond_items == []
        assert absent_total == 0 and absent_items == []
