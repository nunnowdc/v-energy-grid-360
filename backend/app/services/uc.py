"""Caso de uso cadastral da Visão 360 da UC."""

import re

from app.exceptions.uc import InvalidPaginationError, InvalidUCIdError, UCNotFoundError
from app.repositories.uc import UCRepository


def get_cadastro_uc(uc_id: str, repository: UCRepository) -> dict[str, object]:
    """Compõe identificação, medidor e GD sem alterar valores da Gold."""
    if re.fullmatch(r"UC[0-9]{6}", uc_id) is None:
        raise InvalidUCIdError("ID da UC inválido")

    row = repository.get_cadastro(uc_id)
    if row is None:
        raise UCNotFoundError("Unidade consumidora não encontrada")

    return {
        "uc": {
            key: row[key]
            for key in (
                "id_uc",
                "nome_titular",
                "logradouro",
                "numero",
                "bairro",
                "municipio",
                "uf",
                "classe",
            )
        },
        "medidor_atual": (
            {
                key: row[key]
                for key in (
                    "id_medidor_atual",
                    "tipo_medidor_atual",
                    "modelo_medidor_atual",
                    "data_instalacao_medidor_atual",
                )
            }
            if row["id_medidor_atual"] is not None
            else None
        ),
        "geracao_distribuida": {
            key: row[key]
            for key in (
                "possui_gd",
                "data_conexao_gd",
                "potencia_gd_kwp",
                "modalidade_gd",
            )
        },
    }


def get_consumo_e_leituras(
    uc_id: str, pagina_leituras: int, limite: int, repository: UCRepository
) -> dict[str, object]:
    """Prepara gráfico e aba de leituras de uma UC já localizada."""
    offset = validate_pagination(pagina_leituras, limite)
    total, itens = repository.get_leituras_page(uc_id, limite, offset)
    return {
        "consumo_12m": repository.get_consumo_12m(uc_id),
        "historicos": {
            "leituras": {
                "pagina": pagina_leituras,
                "limite": limite,
                "total": total,
                "itens": itens,
            }
        },
    }


def validate_pagination(pagina: int, limite: int) -> int:
    """Valida os limites aprovados e devolve o deslocamento da página."""
    if (
        type(pagina) is not int
        or pagina < 1
        or type(limite) is not int
        or not 1 <= limite <= 50
    ):
        raise InvalidPaginationError("Paginação inválida")
    return (pagina - 1) * limite


def get_faturas(
    uc_id: str, pagina_faturas: int, limite: int, repository: UCRepository
) -> dict[str, object]:
    """Prepara as faturas abertas e a aba paginada de uma UC já localizada."""
    offset = validate_pagination(pagina_faturas, limite)
    abertas = repository.get_faturas_em_aberto(uc_id)
    total, itens = repository.get_faturas_page(uc_id, limite, offset)
    return {
        "faturas_em_aberto": abertas,
        "historicos": {
            "faturas": {
                "pagina": pagina_faturas,
                "limite": limite,
                "total": total,
                "itens": itens,
            }
        },
    }


def get_resumo_faturas_em_aberto(
    uc_id: str, repository: UCRepository
) -> dict[str, object]:
    """Expõe contagem e soma simples do status Gold para composição futura."""
    quantidade, valor_total = repository.get_resumo_faturas_em_aberto(uc_id)
    return {"quantidade": quantidade, "valor_total": valor_total}


def get_interrupcoes_e_chamados(
    uc_id: str,
    pagina_interrupcoes: int,
    pagina_chamados: int,
    limite: int,
    repository: UCRepository,
) -> dict[str, object]:
    """Prepara históricos operacionais independentes de uma UC já localizada."""
    offset_interrupcoes = validate_pagination(pagina_interrupcoes, limite)
    offset_chamados = validate_pagination(pagina_chamados, limite)
    total_interrupcoes, interrupcoes = repository.get_interrupcoes_page(
        uc_id, limite, offset_interrupcoes
    )
    total_chamados, chamados = repository.get_chamados_page(
        uc_id, limite, offset_chamados
    )
    return {
        "historicos": {
            "interrupcoes": {
                "pagina": pagina_interrupcoes,
                "limite": limite,
                "total": total_interrupcoes,
                "itens": interrupcoes,
            },
            "chamados": {
                "pagina": pagina_chamados,
                "limite": limite,
                "total": total_chamados,
                "itens": chamados,
            },
        }
    }


def get_visao_360(
    uc_id: str,
    pagina_faturas: int,
    pagina_interrupcoes: int,
    pagina_chamados: int,
    pagina_leituras: int,
    limite: int,
    repository: UCRepository,
) -> dict[str, object]:
    """Compõe a resposta da UC a partir das projeções Gold já disponíveis."""
    for pagina in (
        pagina_faturas,
        pagina_interrupcoes,
        pagina_chamados,
        pagina_leituras,
    ):
        validate_pagination(pagina, limite)

    cadastro = get_cadastro_uc(uc_id, repository)
    faturas = get_faturas(uc_id, pagina_faturas, limite, repository)
    resumo_faturas = get_resumo_faturas_em_aberto(uc_id, repository)
    consumo_leituras = get_consumo_e_leituras(
        uc_id, pagina_leituras, limite, repository
    )
    operacionais = get_interrupcoes_e_chamados(
        uc_id, pagina_interrupcoes, pagina_chamados, limite, repository
    )

    return {
        **cadastro,
        "faturas_em_aberto": faturas["faturas_em_aberto"],
        "resumo_faturas_em_aberto": resumo_faturas,
        "consumo_12m": consumo_leituras["consumo_12m"],
        "historicos": {
            "faturas": faturas["historicos"]["faturas"],
            "interrupcoes": operacionais["historicos"]["interrupcoes"],
            "chamados": operacionais["historicos"]["chamados"],
            "leituras": consumo_leituras["historicos"]["leituras"],
        },
    }
