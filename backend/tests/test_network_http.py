"""Contrato HTTP da resposta padrão de Continuidade."""

from contextlib import contextmanager, nullcontext
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, TimeoutError

from app.controllers.network import get_network_repository
from app.main import app
from app.schemas.network import NetworkContinuityResponse


def _months() -> list[date]:
    return [
        date(year, month, 1)
        for year, first, last in ((2024, 7, 12), (2025, 1, 12), (2026, 1, 6))
        for month in range(first, last + 1)
    ]


class NetworkGoldFake:
    def months(self) -> list[date]:
        return _months()

    def get_calendar(self) -> list[tuple[date, str]]:
        return [(month, month.strftime("%Y-%m")) for month in self.months()]

    def get_feeders(self) -> list[str]:
        return ["ALM-A", "ALM-B"]

    def get_municipios(self) -> list[str]:
        return ["Recife", "Olinda", "Jaboatao"]

    def get_alimentador_municipio_pairs(self) -> list[tuple[str, str]]:
        return [("ALM-A", "Recife"), ("ALM-B", "Olinda")]

    def get_causas(self) -> list[str]:
        return ["CLIMATICA", "VEGETACAO", "NAO INFORMADA", "NAO IDENTIFICADA"]

    def get_monthly(self, inicio: date, fim: date) -> list[dict[str, object]]:
        rows = []
        for month in self.months():
            for feeder in self.get_feeders():
                compared = month >= date(2025, 7, 1)
                factor = 2 if feeder == "ALM-B" else 1
                rows.append(
                    {
                        "alimentador": feeder,
                        "competencia": month,
                        "mes_referencia": month.strftime("%Y-%m"),
                        "municipio_principal": "Recife",
                        "total_ucs": 100 * factor,
                        "alimentador_pequeno": False,
                        "dec": factor * (1 if compared else 0.5) / 12,
                        "fec": factor * (2 if compared else 1) / 12,
                        "dec_sem_dia_critico": factor * (0.8 if compared else 0.4) / 12,
                        "fec_sem_dia_critico": factor * (1.5 if compared else 0.7) / 12,
                    }
                )
        return [row for row in rows if inicio <= row["competencia"] <= fim]

    def get_occurrence_counts(
        self, inicio: date, fim: date, feeders: list[str], causa: str | None = None
    ) -> list[dict[str, object]]:
        events = [
            {
                "competencia": date(2025, 6, 1),
                "causa": "VEGETACAO",
                "alimentador": "ALM-B",
                "municipio_uc": "Recife",
                "ocorrencias": 3,
            },
            {
                "competencia": date(2026, 6, 1),
                "causa": "VEGETACAO",
                "alimentador": "ALM-B",
                "municipio_uc": "Recife",
                "ocorrencias": 4,
            },
            {
                "competencia": date(2026, 6, 1),
                "causa": "CLIMATICA",
                "alimentador": "ALM-A",
                "municipio_uc": "Olinda",
                "ocorrencias": 2,
            },
        ]
        return [
            {
                "competencia": event["competencia"],
                "causa": event["causa"],
                "ocorrencias": event["ocorrencias"],
            }
            for event in events
            if inicio <= event["competencia"] <= fim
            and event["alimentador"] in feeders
            and (causa is None or event["causa"] == causa)
        ]


def _response(
    gold: NetworkGoldFake | None = None, params: dict[str, str] | None = None
):
    app.dependency_overrides[get_network_repository] = lambda: nullcontext(
        gold or NetworkGoldFake()
    )
    try:
        return TestClient(app).get("/api/network/continuity", params=params)
    finally:
        app.dependency_overrides.clear()


def test_resposta_padrao_tem_cinco_grupos_e_valores_gold() -> None:
    response = _response()

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "periodo",
        "periodo_anterior",
        "ranking",
        "serie",
        "ocorrencias",
    }
    assert body["periodo"] == {"inicio": "2025-07", "fim": "2026-06"}
    assert body["periodo_anterior"] == {"inicio": "2024-07", "fim": "2025-06"}
    assert [row["alimentador"] for row in body["ranking"]] == ["ALM-B", "ALM-A"]
    assert body["ranking"][0]["dec"] == pytest.approx(2)
    assert body["ranking"][0]["fec"] == pytest.approx(4)
    assert body["ranking"][0]["dec_sem_dia_critico"] == pytest.approx(1.6)
    assert body["ranking"][0]["dec_anterior"] == pytest.approx(1)
    assert body["serie"]["alimentador"] == "ALM-B"
    assert len(body["serie"]["atual"]) == len(body["serie"]["anterior"]) == 12
    assert body["serie"]["atual"][0] == {
        "mes_referencia": "2025-07",
        "dec": pytest.approx(2 / 12),
        "fec": pytest.approx(4 / 12),
    }
    assert body["ocorrencias"] == {
        "total": 6,
        "total_anterior": 3,
        "por_causa": [
            {"causa": "VEGETACAO", "ocorrencias": 4},
            {"causa": "CLIMATICA", "ocorrencias": 2},
        ],
    }


def test_periodos_explicitos_nao_consecutivos_aplicam_os_dois_recortes() -> None:
    response = _response(
        params={
            "inicio": "2026-06",
            "fim": "2026-06",
            "inicio_anterior": "2024-07",
            "fim_anterior": "2024-07",
        }
    )

    assert response.status_code == 200
    body = response.json()
    assert body["periodo"] == {"inicio": "2026-06", "fim": "2026-06"}
    assert body["periodo_anterior"] == {"inicio": "2024-07", "fim": "2024-07"}
    assert len(body["serie"]["atual"]) == len(body["serie"]["anterior"]) == 1
    assert body["ranking"][0]["dec"] == pytest.approx(2 / 12, abs=1e-6)
    assert body["ranking"][0]["dec_anterior"] == pytest.approx(1 / 12, abs=1e-6)
    assert body["ocorrencias"] == {
        "total": 6,
        "total_anterior": 0,
        "por_causa": [
            {"causa": "VEGETACAO", "ocorrencias": 4},
            {"causa": "CLIMATICA", "ocorrencias": 2},
        ],
    }


def test_municipio_limita_circuitos_e_ocorrencias_sem_recortar_dec_fec() -> None:
    response = _response(params={"municipio": "Recife"})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "periodo",
        "periodo_anterior",
        "ranking",
        "serie",
        "ocorrencias",
    }
    assert [row["alimentador"] for row in body["ranking"]] == ["ALM-A"]
    assert body["ranking"][0]["dec"] == 1
    assert body["ranking"][0]["fec"] == 2
    assert body["serie"]["alimentador"] == "ALM-A"
    assert body["ocorrencias"] == {
        "total": 2,
        "total_anterior": 0,
        "por_causa": [{"causa": "CLIMATICA", "ocorrencias": 2}],
    }


def test_causa_isolada_filtra_ocorrencias_sem_alterar_ranking_ou_serie() -> None:
    baseline = _response().json()
    response = _response(params={"causa": "VEGETACAO"})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == set(baseline)
    assert body["periodo"] == baseline["periodo"]
    assert body["periodo_anterior"] == baseline["periodo_anterior"]
    assert body["ranking"] == baseline["ranking"]
    assert body["serie"] == baseline["serie"]
    assert body["ocorrencias"] == {
        "total": 4,
        "total_anterior": 3,
        "por_causa": [{"causa": "VEGETACAO", "ocorrencias": 4}],
    }


@pytest.mark.parametrize(
    ("filters", "expected_total", "expected_previous", "expected_feeders"),
    [
        ({"municipio": "Recife", "causa": "CLIMATICA"}, 2, 0, ["ALM-A"]),
        ({"alimentador": "ALM-B", "causa": "VEGETACAO"}, 4, 3, ["ALM-B"]),
        (
            {"municipio": "Olinda", "alimentador": "ALM-B", "causa": "VEGETACAO"},
            4,
            3,
            ["ALM-B"],
        ),
    ],
)
def test_causa_combinada_restringe_somente_ocorrencias(
    filters: dict[str, str],
    expected_total: int,
    expected_previous: int,
    expected_feeders: list[str],
) -> None:
    baseline = _response(
        params={key: value for key, value in filters.items() if key != "causa"}
    ).json()
    response = _response(params=filters)

    assert response.status_code == 200
    body = response.json()
    assert body["ranking"] == baseline["ranking"]
    assert body["serie"] == baseline["serie"]
    assert [row["alimentador"] for row in body["ranking"]] == expected_feeders
    assert body["ocorrencias"] == {
        "total": expected_total,
        "total_anterior": expected_previous,
        "por_causa": [{"causa": filters["causa"], "ocorrencias": expected_total}],
    }


def test_causa_com_periodos_nao_consecutivos_filtra_as_duas_janelas() -> None:
    params = {
        "inicio": "2026-06",
        "fim": "2026-06",
        "inicio_anterior": "2025-06",
        "fim_anterior": "2025-06",
        "municipio": "Olinda",
        "alimentador": "ALM-B",
    }
    baseline = _response(params=params).json()
    response = _response(params={**params, "causa": "VEGETACAO"})

    assert response.status_code == 200
    body = response.json()
    assert body["periodo"] == baseline["periodo"]
    assert body["periodo_anterior"] == baseline["periodo_anterior"]
    assert body["ranking"] == baseline["ranking"]
    assert body["serie"] == baseline["serie"]
    assert body["ocorrencias"] == {
        "total": 4,
        "total_anterior": 3,
        "por_causa": [{"causa": "VEGETACAO", "ocorrencias": 4}],
    }


def test_causa_valida_sem_ocorrencias_retorna_zero_sem_alterar_indicadores() -> None:
    baseline = _response().json()
    response = _response(params={"causa": "NAO INFORMADA"})

    assert response.status_code == 200
    body = response.json()
    assert body["ranking"] == baseline["ranking"]
    assert body["serie"] == baseline["serie"]
    assert body["ocorrencias"] == {
        "total": 0,
        "total_anterior": 0,
        "por_causa": [],
    }


@pytest.mark.parametrize("causa", ["INEXISTENTE", " ", "vegetacao"])
def test_causa_desconhecida_ou_invalida_retorna_422(causa: str) -> None:
    response = _response(params={"causa": causa})

    assert response.status_code == 422


def test_causa_vazia_equivale_a_omissao() -> None:
    assert _response(params={"causa": ""}).json() == _response().json()


def test_causa_repetida_retorna_422_sem_conexao() -> None:
    called = []

    @contextmanager
    def repository_context():
        called.append(True)
        yield NetworkGoldFake()

    app.dependency_overrides[get_network_repository] = lambda: repository_context()
    try:
        response = TestClient(app).get(
            "/api/network/continuity?causa=VEGETACAO&causa=VEGETACAO"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert called == []


def test_nao_informada_e_nao_identificada_permanecem_separadas() -> None:
    class DistinctMissingCauses(NetworkGoldFake):
        def get_occurrence_counts(
            self, inicio: date, fim: date, feeders: list[str], causa: str | None = None
        ) -> list[dict[str, object]]:
            rows = [
                {
                    "competencia": date(2026, 6, 1),
                    "causa": "NAO INFORMADA",
                    "ocorrencias": 2,
                },
                {
                    "competencia": date(2026, 6, 1),
                    "causa": "NAO IDENTIFICADA",
                    "ocorrencias": 3,
                },
            ]
            return [
                row
                for row in rows
                if inicio <= row["competencia"] <= fim
                and (causa is None or row["causa"] == causa)
            ]

    gold = DistinctMissingCauses()
    all_causes = _response(gold).json()["ocorrencias"]
    missing = _response(gold, {"causa": "NAO INFORMADA"}).json()["ocorrencias"]
    unidentified = _response(gold, {"causa": "NAO IDENTIFICADA"}).json()["ocorrencias"]

    assert all_causes["total"] == 5
    assert all_causes["por_causa"] == [
        {"causa": "NAO IDENTIFICADA", "ocorrencias": 3},
        {"causa": "NAO INFORMADA", "ocorrencias": 2},
    ]
    assert missing["por_causa"] == [{"causa": "NAO INFORMADA", "ocorrencias": 2}]
    assert unidentified["por_causa"] == [
        {"causa": "NAO IDENTIFICADA", "ocorrencias": 3}
    ]


def test_distribuicao_sem_filtro_desempata_por_causa_alfabetica() -> None:
    class TiedCauses(NetworkGoldFake):
        def get_occurrence_counts(
            self, inicio: date, fim: date, feeders: list[str], causa: str | None = None
        ) -> list[dict[str, object]]:
            if not inicio <= date(2026, 6, 1) <= fim:
                return []
            rows = [
                {
                    "competencia": date(2026, 6, 1),
                    "causa": "VEGETACAO",
                    "ocorrencias": 2,
                },
                {
                    "competencia": date(2026, 6, 1),
                    "causa": "CLIMATICA",
                    "ocorrencias": 2,
                },
            ]
            return [row for row in rows if causa is None or row["causa"] == causa]

    causes = _response(TiedCauses()).json()["ocorrencias"]["por_causa"]

    assert causes == [
        {"causa": "CLIMATICA", "ocorrencias": 2},
        {"causa": "VEGETACAO", "ocorrencias": 2},
    ]


def test_alimentador_isolado_limita_ranking_serie_e_ocorrencias() -> None:
    response = _response(params={"alimentador": "ALM-B"})

    assert response.status_code == 200
    body = response.json()
    assert [row["alimentador"] for row in body["ranking"]] == ["ALM-B"]
    assert body["serie"]["alimentador"] == "ALM-B"
    assert body["ranking"][0]["dec"] == 2
    assert body["ranking"][0]["fec"] == 4
    assert body["ocorrencias"] == {
        "total": 4,
        "total_anterior": 3,
        "por_causa": [{"causa": "VEGETACAO", "ocorrencias": 4}],
    }


def test_municipio_e_alimentador_compativeis() -> None:
    body = _response(params={"municipio": "Recife", "alimentador": "ALM-A"}).json()

    assert [row["alimentador"] for row in body["ranking"]] == ["ALM-A"]
    assert body["serie"]["alimentador"] == "ALM-A"
    assert body["ocorrencias"]["total"] == 2


def test_alimentador_associado_a_dois_municipios_preserva_indicadores_integrais() -> (
    None
):
    class MultiMunicipioGold(NetworkGoldFake):
        def get_alimentador_municipio_pairs(self) -> list[tuple[str, str]]:
            return [*super().get_alimentador_municipio_pairs(), ("ALM-B", "Recife")]

    gold = MultiMunicipioGold()
    recife = _response(gold, {"municipio": "Recife"})
    olinda = _response(gold, {"municipio": "Olinda"})

    assert recife.status_code == olinda.status_code == 200
    assert [row["alimentador"] for row in recife.json()["ranking"]] == [
        "ALM-B",
        "ALM-A",
    ]
    assert [row["alimentador"] for row in olinda.json()["ranking"]] == ["ALM-B"]
    assert recife.json()["ranking"][0]["dec"] == olinda.json()["ranking"][0]["dec"] == 2
    assert recife.json()["ranking"][0]["fec"] == olinda.json()["ranking"][0]["fec"] == 4
    assert recife.json()["serie"]["alimentador"] == "ALM-B"
    assert olinda.json()["serie"]["alimentador"] == "ALM-B"


def test_ocorrencia_de_uc_em_outro_municipio_entra_pelo_alimentador() -> None:
    class CrossMunicipalityOccurrence(NetworkGoldFake):
        def get_occurrence_counts(
            self,
            inicio: date,
            fim: date,
            feeders: list[str],
            causa: str | None = None,
        ) -> list[dict[str, object]]:
            assert feeders == ["ALM-A"]
            # A UC sintética está em Olinda; o circuito ALM-A atende Recife.
            occurrence = {
                "competencia": date(2026, 6, 1),
                "causa": "CLIMATICA",
                "alimentador": "ALM-A",
                "municipio_uc": "Olinda",
                "ocorrencias": 1,
            }
            if inicio <= occurrence["competencia"] <= fim and (
                causa is None or occurrence["causa"] == causa
            ):
                return [occurrence]
            return []

    body = _response(CrossMunicipalityOccurrence(), {"municipio": "Recife"}).json()

    assert body["ocorrencias"]["total"] == 1
    assert body["ocorrencias"]["por_causa"] == [
        {"causa": "CLIMATICA", "ocorrencias": 1}
    ]


def test_municipio_valido_sem_alimentador_elegivel_retorna_lista_vazia() -> None:
    response = _response(params={"municipio": "Jaboatao"})

    assert response.status_code == 200
    body = response.json()
    assert body["ranking"] == []
    assert body["serie"] is None
    assert body["ocorrencias"] == {
        "total": 0,
        "total_anterior": 0,
        "por_causa": [],
    }


@pytest.mark.parametrize(
    "params",
    [
        {"municipio": "Inexistente"},
        {"alimentador": "ALM-X"},
        {"municipio": " "},
        {"alimentador": " "},
        {"municipio": "Recife", "alimentador": "ALM-B"},
    ],
)
def test_filtros_desconhecidos_ou_incompativeis_retorna_422(
    params: dict[str, str],
) -> None:
    response = _response(params=params)

    assert response.status_code == 422


def test_filtros_vazios_equivalem_a_omissao() -> None:
    expected = _response().json()
    response = _response(params={"municipio": "", "alimentador": ""})

    assert response.status_code == 200
    assert response.json() == expected


def test_filtros_categoricos_com_periodos_personalizados() -> None:
    response = _response(
        params={
            "inicio": "2026-06",
            "fim": "2026-06",
            "inicio_anterior": "2025-06",
            "fim_anterior": "2025-06",
            "municipio": "Recife",
            "alimentador": "ALM-A",
        }
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "periodo",
        "periodo_anterior",
        "ranking",
        "serie",
        "ocorrencias",
    }
    assert [row["alimentador"] for row in body["ranking"]] == ["ALM-A"]
    assert body["serie"]["atual"][0]["mes_referencia"] == "2026-06"
    assert body["serie"]["anterior"][0]["mes_referencia"] == "2025-06"
    assert body["ocorrencias"]["total"] == 2
    assert body["ocorrencias"]["total_anterior"] == 0


def test_openapi_declara_os_sete_parametros_aprovados() -> None:
    operation = app.openapi()["paths"]["/api/network/continuity"]["get"]
    names = {parameter["name"] for parameter in operation["parameters"]}

    assert names == {
        "inicio",
        "fim",
        "inicio_anterior",
        "fim_anterior",
        "municipio",
        "alimentador",
        "causa",
        "vgrid360_access_token",
    }


def test_openapi_explica_periodos_padrao_e_escolhidos() -> None:
    operation = app.openapi()["paths"]["/api/network/continuity"]["get"]
    descriptions = {
        parameter["name"]: parameter["description"]
        for parameter in operation["parameters"]
        if parameter["name"] != "vgrid360_access_token"
    }

    assert "últimos 12 meses" in descriptions["inicio"]
    assert "12 meses imediatamente anteriores" in descriptions["inicio_anterior"]
    assert "período comparado" in descriptions["inicio"]
    assert "período comparado" in descriptions["fim"]
    assert "período base" in descriptions["inicio_anterior"]
    assert "período base" in descriptions["fim_anterior"]
    assert "1 a 24 meses" in descriptions["fim"]
    assert "mesma duração" in descriptions["fim_anterior"]
    assert "não consecutivos" in descriptions["fim_anterior"]


@pytest.mark.parametrize("key", ["municipio", "alimentador"])
def test_filtro_categorico_repetido_retorna_422_sem_conexao(key: str) -> None:
    called = []

    @contextmanager
    def repository_context():
        called.append(True)
        yield NetworkGoldFake()

    app.dependency_overrides[get_network_repository] = lambda: repository_context()
    try:
        response = TestClient(app).get(
            f"/api/network/continuity?{key}=Recife&{key}=Recife"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert called == []


@pytest.mark.parametrize(
    ("inicio", "fim", "inicio_base", "fim_base", "size"),
    [
        ("2026-06", "2026-06", "2026-05", "2026-05", 1),
        ("2026-04", "2026-06", "2026-01", "2026-03", 3),
        ("2026-01", "2026-06", "2025-07", "2025-12", 6),
        ("2025-07", "2026-06", "2024-07", "2025-06", 12),
    ],
)
def test_comparado_explicito_deriva_base_imediata(
    inicio: str, fim: str, inicio_base: str, fim_base: str, size: int
) -> None:
    response = _response(params={"inicio": inicio, "fim": fim})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "periodo",
        "periodo_anterior",
        "ranking",
        "serie",
        "ocorrencias",
    }
    assert body["periodo"] == {"inicio": inicio, "fim": fim}
    assert body["periodo_anterior"] == {"inicio": inicio_base, "fim": fim_base}
    assert len(body["serie"]["atual"]) == len(body["serie"]["anterior"]) == size


def test_dois_periodos_de_24_meses_que_cruzam_anos() -> None:
    class LongGold(NetworkGoldFake):
        def months(self) -> list[date]:
            return [
                date(year, month, 1)
                for year in range(2022, 2027)
                for month in range(1, 13)
                if date(2022, 7, 1) <= date(year, month, 1) <= date(2026, 6, 1)
            ]

    response = _response(
        LongGold(),
        {"inicio": "2024-07", "fim": "2026-06"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["periodo_anterior"] == {"inicio": "2022-07", "fim": "2024-06"}
    assert len(body["serie"]["atual"]) == len(body["serie"]["anterior"]) == 24
    assert body["serie"]["atual"][0]["mes_referencia"] == "2024-07"
    assert body["serie"]["anterior"][-1]["mes_referencia"] == "2024-06"


@pytest.mark.parametrize(
    "params",
    [
        {"inicio": "2026-05"},
        {"fim": "2026-06"},
        {"inicio_anterior": "2025-05"},
        {"fim_anterior": "2025-06"},
        {"inicio_anterior": "2025-05", "fim_anterior": "2025-06"},
        {"inicio": "", "fim": "2026-06"},
        {"inicio": "2026-05", "fim": ""},
        {"inicio": "2026-5", "fim": "2026-06"},
        {"inicio": "2026-06", "fim": "2026-05"},
        {"inicio": "2026-06", "fim": "2024-05"},
        {"inicio": "2024-06", "fim": "2026-06"},
        {"inicio": "2026-05", "fim": "2026-06", "inicio_anterior": "2026-04"},
        {
            "inicio": "2026-05",
            "fim": "2026-06",
            "inicio_anterior": "2026-03",
            "fim_anterior": "2026-03",
        },
        {
            "inicio": "2026-05",
            "fim": "2026-06",
            "inicio_anterior": "2026-04",
            "fim_anterior": "2026-05",
        },
        {
            "inicio": "2026-05",
            "fim": "2026-06",
            "inicio_anterior": "2026-06",
            "fim_anterior": "2026-07",
        },
    ],
)
def test_periodo_invalido_retorna_422_sem_abrir_conexao(params: dict[str, str]) -> None:
    called = []

    @contextmanager
    def repository_context():
        called.append(True)
        yield NetworkGoldFake()

    app.dependency_overrides[get_network_repository] = lambda: repository_context()
    try:
        response = TestClient(app).get("/api/network/continuity", params=params)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert called == []


def test_fim_apos_ultima_competencia_retorna_422() -> None:
    response = _response(params={"inicio": "2026-07", "fim": "2026-07"})

    assert response.status_code == 422
    assert response.json() == {"detail": "Período inválido"}


def test_base_fora_do_calendario_retorna_503_temporal() -> None:
    response = _response(params={"inicio": "2024-07", "fim": "2024-07"})

    assert response.status_code == 503
    assert "calendário Gold" in response.json()["detail"]


def test_base_derivada_antes_do_ano_um_retorna_503_temporal() -> None:
    response = _response(params={"inicio": "0001-01", "fim": "0001-01"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "Recorte temporal indisponível: o calendário Gold não possui "
            "competências suficientes para o período solicitado."
        )
    }


def test_periodo_padrao_sem_12_meses_antes_do_ano_um_retorna_503_temporal() -> None:
    class FirstYearCalendar(NetworkGoldFake):
        def get_calendar(self) -> list[tuple[date, str]]:
            month = date(1, 1, 1)
            return [(month, month.strftime("%Y-%m"))]

    response = _response(FirstYearCalendar())

    assert response.status_code == 503
    assert "calendário Gold" in response.json()["detail"]


def test_lacuna_entre_periodos_nao_afeta_resposta() -> None:
    class GapGold(NetworkGoldFake):
        def get_calendar(self) -> list[tuple[date, str]]:
            return [row for row in super().get_calendar() if row[0] != date(2025, 6, 1)]

    response = _response(
        GapGold(),
        {
            "inicio": "2026-04",
            "fim": "2026-06",
            "inicio_anterior": "2024-10",
            "fim_anterior": "2024-12",
        },
    )

    assert response.status_code == 200
    assert response.json()["periodo_anterior"] == {
        "inicio": "2024-10",
        "fim": "2024-12",
    }


@pytest.mark.parametrize("missing", [date(2024, 11, 1), date(2026, 5, 1)])
def test_lacuna_dentro_de_qualquer_periodo_retorna_503_temporal(
    missing: date,
) -> None:
    class MissingCalendarMonth(NetworkGoldFake):
        def get_calendar(self) -> list[tuple[date, str]]:
            return [row for row in super().get_calendar() if row[0] != missing]

    response = _response(
        MissingCalendarMonth(),
        {
            "inicio": "2026-04",
            "fim": "2026-06",
            "inicio_anterior": "2024-10",
            "fim_anterior": "2024-12",
        },
    )

    assert response.status_code == 503
    assert "calendário Gold" in response.json()["detail"]


def test_denominador_pode_mudar_entre_periodos_sem_alterar_dec_gold() -> None:
    class DifferentDenominator(NetworkGoldFake):
        def get_monthly(self, inicio: date, fim: date) -> list[dict[str, object]]:
            rows = super().get_monthly(inicio, fim)
            if fim < date(2025, 7, 1):
                for row in rows:
                    row["total_ucs"] = row["total_ucs"] + 1
            return rows

    response = _response(DifferentDenominator())

    assert response.status_code == 200
    assert response.json()["ranking"][0]["total_ucs"] == 200


def test_parametros_temporais_repetidos_retorna_422_antes_da_gold() -> None:
    called = []

    @contextmanager
    def repository_context():
        called.append(True)
        yield NetworkGoldFake()

    app.dependency_overrides[get_network_repository] = lambda: repository_context()
    try:
        response = TestClient(app).get(
            "/api/network/continuity?inicio=2026-06&inicio=2026-06&fim=2026-06"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert called == []


def test_contrato_aninhado_e_rota_unica() -> None:
    body = _response().json()

    assert set(body["ranking"][0]) == {
        "alimentador",
        "municipio_principal",
        "total_ucs",
        "alimentador_pequeno",
        "dec",
        "fec",
        "dec_sem_dia_critico",
        "dec_anterior",
    }
    assert set(body["serie"]) == {"alimentador", "atual", "anterior"}
    assert set(body["serie"]["atual"][0]) == {"mes_referencia", "dec", "fec"}
    assert set(body["ocorrencias"]) == {"total", "total_anterior", "por_causa"}
    assert [row["mes_referencia"] for row in body["serie"]["atual"]] == [
        month.strftime("%Y-%m") for month in _months()[12:]
    ]
    assert "/api/network/continuity" in app.openapi()["paths"]
    assert "id_uc" not in str(body)
    assert "variacao_pct" not in str(body)


def test_ranking_usa_precisao_integral_antes_de_arredondar() -> None:
    class NearlyTiedGold(NetworkGoldFake):
        def get_monthly(self, inicio: date, fim: date) -> list[dict[str, object]]:
            rows = super().get_monthly(inicio, fim)
            for row in rows:
                if row["competencia"] >= date(2025, 7, 1):
                    row["dec"] = 0.0
            for row in rows:
                if row["competencia"] == date(2026, 6, 1):
                    row["dec"] = (
                        1.00000041 if row["alimentador"] == "ALM-A" else 1.00000049
                    )
            return rows

    body = _response(NearlyTiedGold()).json()

    assert [row["alimentador"] for row in body["ranking"]] == ["ALM-B", "ALM-A"]
    assert [row["dec"] for row in body["ranking"]] == [1.0, 1.0]
    assert body["serie"]["alimentador"] == "ALM-B"
    assert body["serie"]["atual"][-1]["dec"] == 1.00000049


def test_sem_ocorrencias_retorna_zero_real_e_lista_vazia() -> None:
    class NoOccurrences(NetworkGoldFake):
        def get_occurrence_counts(
            self,
            inicio: date,
            fim: date,
            feeders: list[str],
            causa: str | None = None,
        ) -> list[dict[str, object]]:
            return []

    body = _response(NoOccurrences()).json()

    assert body["ocorrencias"] == {
        "total": 0,
        "total_anterior": 0,
        "por_causa": [],
    }
    assert len(body["ranking"]) == 2


def test_calendario_insuficiente_retorna_503_especifico() -> None:
    class ShortCalendar(NetworkGoldFake):
        def get_calendar(self) -> list[tuple[date, str]]:
            return super().get_calendar()[1:]

    response = _response(ShortCalendar())

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "Recorte temporal indisponível: o calendário Gold não possui "
            "competências suficientes para o período solicitado."
        )
    }


def test_mes_de_alimentador_ausente_nao_vira_indicador_zero() -> None:
    class MissingFeederMonth(NetworkGoldFake):
        def get_monthly(self, inicio: date, fim: date) -> list[dict[str, object]]:
            return [
                row
                for row in super().get_monthly(inicio, fim)
                if not (
                    row["alimentador"] == "ALM-B"
                    and row["competencia"] == date(2026, 6, 1)
                )
            ]

    response = _response(MissingFeederMonth())

    assert response.status_code == 503
    assert response.json() == {"detail": "Gold indisponível"}


def test_denominador_malformado_na_gold_retorna_503() -> None:
    class MalformedDenominator(NetworkGoldFake):
        def get_monthly(self, inicio: date, fim: date) -> list[dict[str, object]]:
            rows = super().get_monthly(inicio, fim)
            rows[0]["total_ucs"] = []
            return rows

    response = _response(MalformedDenominator())

    assert response.status_code == 503
    assert response.json() == {"detail": "Gold indisponível"}


def test_soma_nao_finita_de_indicadores_gold_retorna_503() -> None:
    class OverflowedGold(NetworkGoldFake):
        def get_monthly(self, inicio: date, fim: date) -> list[dict[str, object]]:
            rows = super().get_monthly(inicio, fim)
            for row in rows:
                row["dec"] = 1e308
            return rows

    response = _response(OverflowedGold())

    assert response.status_code == 503
    assert response.json() == {"detail": "Gold indisponível"}


@pytest.mark.parametrize("fault", ["empty", "duplicate", "label", "gap"])
def test_calendario_invalido_retorna_503_temporal(fault: str) -> None:
    class InvalidCalendar(NetworkGoldFake):
        def get_calendar(self) -> list[tuple[date, str]]:
            rows = super().get_calendar()
            if fault == "empty":
                return []
            if fault == "duplicate":
                return [*rows, rows[-1]]
            if fault == "label":
                rows[-1] = (rows[-1][0], "mês incorreto")
                return rows
            return [row for row in rows if row[0] != date(2026, 5, 1)]

    response = _response(InvalidCalendar())

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "Recorte temporal indisponível: o calendário Gold não possui "
            "competências suficientes para o período solicitado."
        )
    }


@pytest.mark.parametrize(
    ("fault", "key"),
    [
        ("duplicate", None),
        ("missing", None),
        ("null", "dec"),
        ("negative_indicator", "dec"),
        ("nan", "fec"),
        ("infinite", "dec_sem_dia_critico"),
        ("null", "fec_sem_dia_critico"),
        ("zero", "total_ucs"),
        ("negative", "total_ucs"),
        ("variable", "total_ucs"),
    ],
)
def test_medida_gold_inconsistente_retorna_503(fault: str, key: str | None) -> None:
    class InvalidMonthly(NetworkGoldFake):
        def get_monthly(self, inicio: date, fim: date) -> list[dict[str, object]]:
            rows = super().get_monthly(inicio, fim)
            if fault == "duplicate":
                return [*rows, rows[0].copy()]
            if fault == "missing":
                return rows[1:]
            if fault == "null":
                rows[0][key] = None
            elif fault == "nan":
                rows[0][key] = float("nan")
            elif fault == "negative_indicator":
                rows[0][key] = -0.1
            elif fault == "infinite":
                rows[0][key] = float("inf")
            elif fault == "zero":
                rows[0][key] = 0
            elif fault == "negative":
                rows[0][key] = -1
            else:
                rows[0][key] = 999
            return rows

    response = _response(InvalidMonthly())

    assert response.status_code == 503
    assert response.json() == {"detail": "Gold indisponível"}


def test_zero_publicado_na_gold_e_valor_valido() -> None:
    class ZeroIndicators(NetworkGoldFake):
        def get_monthly(self, inicio: date, fim: date) -> list[dict[str, object]]:
            rows = super().get_monthly(inicio, fim)
            for row in rows:
                for key in ("dec", "fec", "dec_sem_dia_critico", "fec_sem_dia_critico"):
                    row[key] = 0.0
            return rows

    response = _response(ZeroIndicators())

    assert response.status_code == 200
    assert [row["alimentador"] for row in response.json()["ranking"]] == [
        "ALM-A",
        "ALM-B",
    ]
    assert all(
        row["dec"] == row["fec"] == row["dec_anterior"] == 0
        for row in response.json()["ranking"]
    )


def test_openapi_documenta_ambos_os_503_e_erros_422_500() -> None:
    operation = app.openapi()["paths"]["/api/network/continuity"]["get"]
    responses = operation["responses"]

    assert {"200", "422", "503", "500"} <= responses.keys()
    examples = responses["503"]["content"]["application/json"]["examples"]
    assert {item["value"]["detail"] for item in examples.values()} == {
        "Gold indisponível",
        (
            "Recorte temporal indisponível: o calendário Gold não possui "
            "competências suficientes para o período solicitado."
        ),
    }


def test_contexto_de_conexao_fecha_em_sucesso_e_503_de_integridade() -> None:
    closed = []

    class InvalidCalendarForContext(NetworkGoldFake):
        def get_calendar(self) -> list[tuple[date, str]]:
            return []

    @contextmanager
    def repository_context(gold: NetworkGoldFake):
        try:
            yield gold
        finally:
            closed.append(True)

    def override_for(gold: NetworkGoldFake):
        return lambda: repository_context(gold)

    for gold, expected_status in (
        (NetworkGoldFake(), 200),
        (InvalidCalendarForContext(), 503),
    ):
        app.dependency_overrides[get_network_repository] = override_for(gold)
        try:
            response = TestClient(app).get("/api/network/continuity")
        finally:
            app.dependency_overrides.clear()
        assert response.status_code == expected_status
    assert closed == [True, True]


def test_timeout_retorna_503_e_libera_contexto() -> None:
    closed = []

    class TimedOutGold(NetworkGoldFake):
        def get_calendar(self) -> list[tuple[date, str]]:
            raise TimeoutError("detalhe interno")

    @contextmanager
    def repository_context():
        try:
            yield TimedOutGold()
        finally:
            closed.append(True)

    app.dependency_overrides[get_network_repository] = lambda: repository_context()
    try:
        response = TestClient(app).get("/api/network/continuity")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Gold indisponível"}
    assert closed == [True]


def test_falha_de_validacao_da_resposta_retorna_500_e_libera_contexto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed = []

    @contextmanager
    def repository_context():
        try:
            yield NetworkGoldFake()
        finally:
            closed.append(True)

    def invalid_response(_cls: type, _result: dict[str, object]) -> None:
        raise ValueError("estrutura interna inválida")

    monkeypatch.setattr(
        NetworkContinuityResponse, "model_validate", classmethod(invalid_response)
    )
    app.dependency_overrides[get_network_repository] = lambda: repository_context()
    try:
        response = TestClient(app).get("/api/network/continuity")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno"}
    assert closed == [True]


def test_falha_de_banco_retorna_503_sem_vazar_detalhes_e_libera_contexto() -> None:
    closed = []

    class DatabaseFailure(NetworkGoldFake):
        def get_calendar(self) -> list[tuple[date, str]]:
            raise OperationalError("SELECT segredo", None, Exception("senha secreta"))

    @contextmanager
    def repository_context():
        try:
            yield DatabaseFailure()
        finally:
            closed.append(True)

    app.dependency_overrides[get_network_repository] = lambda: repository_context()
    try:
        response = TestClient(app).get("/api/network/continuity")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Gold indisponível"}
    assert closed == [True]


def test_falha_inesperada_retorna_500_generico_e_libera_contexto() -> None:
    closed = []

    class UnexpectedFailure(NetworkGoldFake):
        def get_calendar(self) -> list[tuple[date, str]]:
            raise ValueError("detalhe interno")

    @contextmanager
    def repository_context():
        try:
            yield UnexpectedFailure()
        finally:
            closed.append(True)

    app.dependency_overrides[get_network_repository] = lambda: repository_context()
    try:
        response = TestClient(app).get("/api/network/continuity")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno"}
    assert closed == [True]


def test_parametro_desconhecido_retorna_422_sem_abrir_conexao() -> None:
    called = []

    @contextmanager
    def repository_context():
        called.append(True)
        yield NetworkGoldFake()

    app.dependency_overrides[get_network_repository] = lambda: repository_context()
    try:
        response = TestClient(app).get(
            "/api/network/continuity", params={"nao_previsto": "x"}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert called == []
