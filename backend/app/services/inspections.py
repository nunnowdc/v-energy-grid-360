"""Composição da fila Gold sem recalcular os valores analíticos."""

from datetime import UTC, datetime

from app.repositories.inspection_orders import (
    ActiveOrderRaceError,
    InspectionOrdersRepository,
)
from app.repositories.inspections import InspectionsRepository


class InvalidQueueFilterError(ValueError):
    """Parâmetro categórico não pertence ao catálogo Gold."""


class QueueSnapshotUnavailableError(Exception):
    """O snapshot Gold não sustenta a resposta da fila."""


class InvalidOrderBatchError(ValueError):
    """O lote contém IDs inválidos, inexistentes ou fora da fila Gold."""


class ActiveOrderConflictError(Exception):
    """Uma ou mais UCs já possuem ordem ativa."""

    def __init__(self, ids_uc: list[str]) -> None:
        self.ids_uc = ids_uc
        super().__init__("Já existe ordem ativa para as UCs: " + ", ".join(ids_uc))


class OrderNotFoundError(Exception):
    """A ordem solicitada não existe."""


class InvalidOrderTransitionError(Exception):
    """A transição não pertence à máquina de estados aprovada."""


def change_inspection_order(
    orders: InspectionOrdersRepository,
    order_id: int,
    status: str,
    resultado: str | None = None,
) -> dict[str, object]:
    allowed = {
        ("ABERTA", "EM_CAMPO"),
        ("ABERTA", "CANCELADA"),
        ("EM_CAMPO", "CONCLUIDA"),
        ("EM_CAMPO", "CANCELADA"),
    }
    with orders.transaction():
        current = orders.get_order(order_id)
        if current is None:
            raise OrderNotFoundError
        if (current["status"], status) not in allowed:
            raise InvalidOrderTransitionError
        if not orders.update_if_status(order_id, current["status"], status, resultado):
            if orders.get_order(order_id) is None:
                raise OrderNotFoundError
            raise InvalidOrderTransitionError
        row = orders.get_order(order_id)
        if row is None:
            raise RuntimeError("Ordem desapareceu durante a transição")
        timestamp = row["criada_em"]
        if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
            raise RuntimeError("Timestamp operacional inválido")
        if not isinstance(row["municipio"], str) or not isinstance(row["bairro"], str):
            raise QueueSnapshotUnavailableError
        return {
            "id_ordem": f"OI-{row['id']:05d}",
            "id_uc": row["id_uc"],
            "municipio": row["municipio"],
            "bairro": row["bairro"],
            "status": row["status"],
            "resultado": row["resultado"],
            "criada_em": timestamp.astimezone(UTC),
        }


def _validate_filters(
    repository: InspectionsRepository,
    municipio: str | None,
    bairro: str | None,
    classe: str | None,
) -> tuple[str | None, str | None, str | None]:
    municipio, bairro, classe = (value or None for value in (municipio, bairro, classe))
    if bairro is not None and municipio is None:
        raise InvalidQueueFilterError("Bairro exige município")
    pairs, classes = repository.get_catalog()
    if municipio is not None and municipio not in {name for name, _ in pairs}:
        raise InvalidQueueFilterError("Município desconhecido")
    if bairro is not None and (municipio, bairro) not in pairs:
        raise InvalidQueueFilterError("Bairro incompatível com município")
    if classe is not None and classe not in classes:
        raise InvalidQueueFilterError("Classe desconhecida")
    return municipio, bairro, classe


def list_inspection_orders(
    gold: InspectionsRepository,
    orders: InspectionOrdersRepository,
    municipio: str | None,
    bairro: str | None,
    classe: str | None,
) -> dict[str, object]:
    municipio, bairro, classe = _validate_filters(gold, municipio, bairro, classe)
    rows = orders.list_orders(municipio, bairro, classe)
    if len({row["id"] for row in rows}) != len(rows):
        raise QueueSnapshotUnavailableError
    items = []
    for row in rows:
        timestamp = row["criada_em"]
        if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
            raise QueueSnapshotUnavailableError
        if not isinstance(row["municipio"], str) or not isinstance(row["bairro"], str):
            raise QueueSnapshotUnavailableError
        items.append(
            {
                "id_ordem": f"OI-{row['id']:05d}",
                "id_uc": row["id_uc"],
                "municipio": row["municipio"],
                "bairro": row["bairro"],
                "status": row["status"],
                "resultado": row["resultado"],
                "criada_em": timestamp.astimezone(UTC),
            }
        )
    return {"itens": items}


def create_inspection_orders(
    gold: InspectionsRepository,
    orders: InspectionOrdersRepository,
    ids_uc: list[str],
) -> dict[str, object]:
    if len(ids_uc) != len(set(ids_uc)):
        raise InvalidOrderBatchError("IDs de UC repetidos no lote")

    try:
        with orders.transaction():
            if gold.get_snapshot_date() is None:
                raise QueueSnapshotUnavailableError
            existing = gold.get_existing_uc_ids(ids_uc)
            missing = [uc for uc in ids_uc if uc not in existing]
            if missing:
                raise InvalidOrderBatchError("UC inexistente: " + ", ".join(missing))
            eligible_rows = gold.get_eligible_units(ids_uc)
            eligible = {row["id_uc"]: row for row in eligible_rows}
            outside = [uc for uc in ids_uc if uc not in eligible]
            if outside:
                raise InvalidOrderBatchError(
                    "UC fora da fila Gold: " + ", ".join(outside)
                )
            if len(eligible_rows) != len(eligible):
                raise QueueSnapshotUnavailableError
            for row in eligible_rows:
                if not isinstance(row["municipio"], str) or not isinstance(
                    row["bairro"], str
                ):
                    raise QueueSnapshotUnavailableError

            active = orders.get_active_orders(ids_uc)
            if active:
                active_ids = {row["id_uc"] for row in active}
                raise ActiveOrderConflictError(
                    [uc for uc in ids_uc if uc in active_ids]
                )

            created_rows = orders.insert_orders(ids_uc)
            if len(created_rows) != len(ids_uc):
                raise RuntimeError("Inserção incompleta de ordens")
            created = {row["id_uc"]: row for row in created_rows}
            if len(created) != len(ids_uc):
                raise RuntimeError("Inserção inconsistente de ordens")
            response = []
            for uc in ids_uc:
                row = created[uc]
                timestamp = row["criada_em"]
                if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
                    raise RuntimeError("Timestamp operacional inválido")
                response.append(
                    {
                        "id_ordem": f"OI-{row['id']:05d}",
                        "id_uc": uc,
                        "municipio": eligible[uc]["municipio"],
                        "bairro": eligible[uc]["bairro"],
                        "status": row["status"],
                        "resultado": row["resultado"],
                        "criada_em": timestamp.astimezone(UTC),
                    }
                )
    except ActiveOrderRaceError as exc:
        active_ids = {row["id_uc"] for row in orders.get_active_orders(ids_uc)}
        conflicts = [uc for uc in ids_uc if uc in active_ids]
        raise ActiveOrderConflictError(conflicts or ids_uc) from exc

    return {"ordens": response}


def get_inspection_queue(
    repository: InspectionsRepository,
    municipio: str | None,
    bairro: str | None,
    classe: str | None,
    pagina: int,
    limite: int,
) -> dict[str, object]:
    municipio, bairro, classe = _validate_filters(repository, municipio, bairro, classe)

    data_referencia = repository.get_snapshot_date()
    if data_referencia is None:
        raise QueueSnapshotUnavailableError

    summary = repository.get_summary(municipio, bairro, classe)
    total = summary["ucs"]
    medidas = summary["medidas"]
    energia = summary["kwh_recuperavel_estimado_ano"]
    if not isinstance(total, int) or not isinstance(medidas, int) or medidas != total:
        raise QueueSnapshotUnavailableError
    if total == 0:
        energia = 0.0
    elif energia is None:
        raise QueueSnapshotUnavailableError

    offset = (pagina - 1) * limite
    rows = (
        repository.get_items(municipio, bairro, classe, limite, offset)
        if offset < total
        else []
    )
    active_orders = repository.orders.get_active_orders([row["id_uc"] for row in rows])
    active_by_uc = {
        row["id_uc"]: {"id_ordem": f"OI-{row['id']:05d}", "status": row["status"]}
        for row in active_orders
    }
    return {
        "data_referencia": data_referencia,
        "resumo": {"ucs": total, "kwh_recuperavel_estimado_ano": energia},
        "pagina": pagina,
        "limite": limite,
        "total": total,
        "itens": [
            {**row, "ordem_aberta": active_by_uc.get(row["id_uc"])} for row in rows
        ],
    }
