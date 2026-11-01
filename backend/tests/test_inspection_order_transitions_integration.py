"""Transições HTTP persistidas apenas em PostgreSQL descartável com Gold sintética."""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date
from threading import Barrier, Lock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from test_inspection_orders_postgres import ADMIN_DE_TESTE

from app.controllers.inspections import (
    get_inspections_repository,
    get_order_repositories,
)
from app.main import app
from app.repositories.inspection_orders import (
    ORDENS_INSPECAO,
    InspectionOrdersRepository,
)
from app.repositories.inspections import InspectionsRepository
from app.security.dependencies import get_current_user

pytest_plugins = ("test_inspection_orders_postgres",)


@pytest.fixture(scope="module")
def transition_engine(orders_engine: Engine) -> Engine:
    with orders_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE dim_unidade_consumidora ("
            "id_uc TEXT PRIMARY KEY, municipio TEXT, bairro TEXT, classe TEXT)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE fila_inspecao ("
            "id_uc TEXT PRIMARY KEY, data_referencia DATE NOT NULL, "
            "prioridade INTEGER NOT NULL, score INTEGER NOT NULL, "
            "motivo_suspeita TEXT NOT NULL, "
            "kwh_recuperavel_estimado_ano DOUBLE PRECISION NOT NULL, "
            "municipio TEXT NOT NULL, bairro TEXT NOT NULL, classe TEXT NOT NULL)"
        )
        units = [f"UC901{number:03d}" for number in range(101, 108)]
        connection.execute(
            text(
                "INSERT INTO dim_unidade_consumidora "
                "(id_uc, municipio, bairro, classe) VALUES "
                "(:id_uc, 'Recife', 'Boa Viagem', 'RESIDENCIAL')"
            ),
            [{"id_uc": uc} for uc in units],
        )
        connection.execute(
            text(
                "INSERT INTO fila_inspecao "
                "(id_uc, data_referencia, prioridade, score, motivo_suspeita, "
                "kwh_recuperavel_estimado_ano, municipio, bairro, classe) VALUES "
                "(:id_uc, :reference, :priority, 70, 'Sintético', 120.5, "
                "'Recife', 'Boa Viagem', 'RESIDENCIAL')"
            ),
            [
                {"id_uc": uc, "reference": date(2026, 6, 1), "priority": position}
                for position, uc in enumerate(units, start=1)
            ],
        )
    return orders_engine


@contextmanager
def _client(engine: Engine) -> Iterator[TestClient]:
    @contextmanager
    def order_repositories():
        with engine.connect() as connection:
            gold = InspectionsRepository(connection)
            yield gold, gold.orders

    @contextmanager
    def queue_repository():
        with engine.connect() as connection:
            yield InspectionsRepository(connection)

    app.dependency_overrides[get_order_repositories] = lambda: order_repositories()
    app.dependency_overrides[get_inspections_repository] = lambda: queue_repository()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _order_row(engine: Engine, external_id: str):
    with engine.connect() as connection:
        return connection.execute(
            select(ORDENS_INSPECAO).where(ORDENS_INSPECAO.c.id == int(external_id[3:]))
        ).one()


def test_field_completion_and_new_order_after_terminal_state(
    transition_engine: Engine,
) -> None:
    with _client(transition_engine) as client:
        created = client.post("/api/inspections/order", json={"ids_uc": ["UC901101"]})
        assert created.status_code == 201
        id_ordem = created.json()["ordens"][0]["id_ordem"]
        initial = _order_row(transition_engine, id_ordem)

        field = client.patch(
            f"/api/inspections/{id_ordem}", json={"status": "EM_CAMPO"}
        )
        assert field.status_code == 200
        in_field = _order_row(transition_engine, id_ordem)
        assert in_field.status == "EM_CAMPO"
        assert in_field.resultado is None and in_field.concluida_em is None
        assert in_field.atualizada_em > initial.atualizada_em
        assert in_field.criada_em == initial.criada_em

        completed = client.patch(
            f"/api/inspections/{id_ordem}",
            json={"status": "CONCLUIDA", "resultado": "IRREGULARIDADE_CONFIRMADA"},
        )
        assert completed.status_code == 200
        assert completed.json()["resultado"] == "IRREGULARIDADE_CONFIRMADA"
        finished = _order_row(transition_engine, id_ordem)
        assert finished.status == "CONCLUIDA"
        assert finished.concluida_em is not None
        assert finished.atualizada_em > in_field.atualizada_em
        assert finished.criada_em == initial.criada_em
        assert finished.concluida_em.tzinfo is not None
        assert completed.json()["criada_em"].endswith(("Z", "+00:00"))

        history = client.get("/api/inspections/orders")
        assert history.status_code == 200
        assert any(item["id_ordem"] == id_ordem for item in history.json()["itens"])
        queue = client.get("/api/inspections/queue")
        item = next(
            item for item in queue.json()["itens"] if item["id_uc"] == "UC901101"
        )
        assert item["ordem_aberta"] is None
        assert (
            client.post(
                "/api/inspections/order", json={"ids_uc": ["UC901101"]}
            ).status_code
            == 201
        )


@pytest.mark.parametrize(
    ("uc", "move_first"), [("UC901102", False), ("UC901103", True)]
)
def test_delete_cancels_logically_and_releases_uc(
    transition_engine: Engine, uc: str, move_first: bool
) -> None:
    with _client(transition_engine) as client:
        created = client.post("/api/inspections/order", json={"ids_uc": [uc]})
        id_ordem = created.json()["ordens"][0]["id_ordem"]
        before = _order_row(transition_engine, id_ordem)
        if move_first:
            assert (
                client.patch(
                    f"/api/inspections/{id_ordem}", json={"status": "EM_CAMPO"}
                ).status_code
                == 200
            )
        canceled = client.delete(f"/api/inspections/{id_ordem}")
        assert canceled.status_code == 200
        assert canceled.json()["status"] == "CANCELADA"
        row = _order_row(transition_engine, id_ordem)
        assert row.status == "CANCELADA"
        assert row.resultado is None and row.concluida_em is None
        assert row.atualizada_em > before.atualizada_em
        assert row.criada_em == before.criada_em
        history = client.get("/api/inspections/orders").json()["itens"]
        assert any(
            item["id_ordem"] == id_ordem and item["status"] == "CANCELADA"
            for item in history
        )
        queue = client.get("/api/inspections/queue").json()["itens"]
        assert (
            next(item for item in queue if item["id_uc"] == uc)["ordem_aberta"] is None
        )
        assert (
            client.post("/api/inspections/order", json={"ids_uc": [uc]}).status_code
            == 201
        )


def test_second_canonical_result_persists(transition_engine: Engine) -> None:
    with _client(transition_engine) as client:
        created = client.post("/api/inspections/order", json={"ids_uc": ["UC901104"]})
        id_ordem = created.json()["ordens"][0]["id_ordem"]
        assert (
            client.patch(
                f"/api/inspections/{id_ordem}", json={"status": "EM_CAMPO"}
            ).status_code
            == 200
        )
        response = client.patch(
            f"/api/inspections/{id_ordem}",
            json={"status": "CONCLUIDA", "resultado": "SEM_IRREGULARIDADE"},
        )
        assert response.status_code == 200
        assert _order_row(transition_engine, id_ordem).resultado == "SEM_IRREGULARIDADE"


def test_failure_after_update_rolls_back(
    transition_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = InspectionOrdersRepository.get_order
    calls = 0

    def fail_after_update(self: InspectionOrdersRepository, order_id: int):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("falha sintética após UPDATE")
        return original(self, order_id)

    with _client(transition_engine) as client:
        created = client.post("/api/inspections/order", json={"ids_uc": ["UC901105"]})
        id_ordem = created.json()["ordens"][0]["id_ordem"]
        before = _order_row(transition_engine, id_ordem)
        monkeypatch.setattr(InspectionOrdersRepository, "get_order", fail_after_update)
        response = client.patch(
            f"/api/inspections/{id_ordem}", json={"status": "EM_CAMPO"}
        )
    assert response.status_code == 500
    after = _order_row(transition_engine, id_ordem)
    assert after.status == "ABERTA"
    assert after.atualizada_em == before.atualizada_em


def test_concurrent_patch_and_delete_only_one_wins(
    transition_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = InspectionOrdersRepository.update_if_status
    barrier = Barrier(2)
    lock = Lock()
    calls = 0

    def synchronized_update(
        self, order_id, expected_status, status, resultado, **kwargs
    ):
        nonlocal calls
        with lock:
            calls += 1
            should_wait = calls <= 2
        if should_wait:
            barrier.wait(timeout=3)
        return original(self, order_id, expected_status, status, resultado, **kwargs)

    with _client(transition_engine) as client:
        created = client.post("/api/inspections/order", json={"ids_uc": ["UC901106"]})
        id_ordem = created.json()["ordens"][0]["id_ordem"]
        monkeypatch.setattr(
            InspectionOrdersRepository, "update_if_status", synchronized_update
        )
        with ThreadPoolExecutor(max_workers=2) as executor:
            patch = executor.submit(
                client.patch,
                f"/api/inspections/{id_ordem}",
                json={"status": "EM_CAMPO"},
            )
            delete = executor.submit(client.delete, f"/api/inspections/{id_ordem}")
            results = [patch.result(), delete.result()]
    assert sorted(result.status_code for result in results) == [200, 409]
    row = _order_row(transition_engine, id_ordem)
    assert row.status in {"EM_CAMPO", "CANCELADA"}
    assert row.resultado is None and row.concluida_em is None
    with transition_engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM ordens_inspecao WHERE id_uc = 'UC901106'")
            ).scalar_one()
            == 1
        )


def test_order_keeps_who_created_it_and_who_changed_it_last(
    transition_engine: Engine,
) -> None:
    perdas = {
        "id": UUID("7a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d"),
        "nome": "Pessoa de Perdas",
        "email": "perdas@example.invalid",
        "perfil": "PERDAS",
    }
    with transition_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO usuarios (id, nome, email, senha_hash, perfil, criado_em) "
                "VALUES (:id, :nome, :email, 'sem-senha', :perfil, now())"
            ),
            perdas,
        )

    with _client(transition_engine) as client:
        created = client.post("/api/inspections/order", json={"ids_uc": ["UC901107"]})
        assert created.status_code == 201
        id_ordem = created.json()["ordens"][0]["id_ordem"]
        nova = _order_row(transition_engine, id_ordem)
        assert str(nova.criada_por) == ADMIN_DE_TESTE
        assert str(nova.atualizada_por) == ADMIN_DE_TESTE
        assert created.json()["ordens"][0]["criada_por_nome"] == (
            "Administrador de teste"
        )

        # Outra pessoa da equipe manda a ordem para campo
        app.dependency_overrides[get_current_user] = lambda: perdas
        field = client.patch(
            f"/api/inspections/{id_ordem}", json={"status": "EM_CAMPO"}
        )
        assert field.status_code == 200
        listed = client.get("/api/inspections/orders").json()["itens"]

    em_campo = _order_row(transition_engine, id_ordem)
    assert str(em_campo.criada_por) == ADMIN_DE_TESTE
    assert em_campo.atualizada_por == perdas["id"]
    # A API devolve o nome, nunca o id da conta
    assert field.json()["criada_por_nome"] == "Administrador de teste"
    assert field.json()["atualizada_por_nome"] == "Pessoa de Perdas"
    assert "criada_por" not in field.json()
    item = next(item for item in listed if item["id_ordem"] == id_ordem)
    assert (item["criada_por_nome"], item["atualizada_por_nome"]) == (
        "Administrador de teste",
        "Pessoa de Perdas",
    )
