"""Projeção de leitura da UC na Gold, sem modelo ORM."""

from collections.abc import Mapping

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import InterfaceError, OperationalError, TimeoutError

from app.exceptions.uc import GoldUnavailableError


class UCRepository:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def get_cadastro(self, uc_id: str) -> Mapping[str, object] | None:
        """Busca uma única UC pelo ID completo, sem JOINs históricos."""
        query = text(
            """
            SELECT id_uc, nome_titular, logradouro, numero, bairro, municipio,
                   uf, classe, id_medidor_atual, tipo_medidor_atual,
                   modelo_medidor_atual, data_instalacao_medidor_atual,
                   possui_gd, data_conexao_gd, potencia_gd_kwp, modalidade_gd
            FROM dim_unidade_consumidora
            WHERE id_uc = :uc_id
            """
        )
        try:
            row = (
                self.connection.execute(query, {"uc_id": uc_id})
                .mappings()
                .one_or_none()
            )
        except (InterfaceError, OperationalError, TimeoutError) as exc:
            raise GoldUnavailableError("Gold indisponível") from exc
        return dict(row) if row is not None else None

    def get_consumo_12m(self, uc_id: str) -> list[dict[str, object]]:
        """Devolve o calendário Gold mais recente e suas medidas já publicadas."""
        query = text(
            """
            SELECT calendario.mes_referencia, leitura.consumo_kwh,
                   leitura.consumo_ano_anterior_kwh,
                   leitura.variacao_ano_anterior_pct
            FROM (
                SELECT competencia, mes_referencia
                FROM dim_competencia
                ORDER BY competencia DESC
                LIMIT 12
            ) AS calendario
            LEFT JOIN fact_leituras AS leitura
              ON leitura.id_uc = :uc_id
             AND leitura.competencia = calendario.competencia
            ORDER BY calendario.competencia ASC
            """
        )
        try:
            rows = self.connection.execute(query, {"uc_id": uc_id}).mappings().all()
        except (InterfaceError, OperationalError, TimeoutError) as exc:
            raise GoldUnavailableError("Gold indisponível") from exc
        return [dict(row) for row in rows]

    def get_leituras_page(
        self, uc_id: str, limite: int, offset: int
    ) -> tuple[int, list[dict[str, object]]]:
        """Conta e consulta uma página do histórico de leituras da UC."""
        count_query = text("SELECT count(*) FROM fact_leituras WHERE id_uc = :uc_id")
        page_query = text(
            """
            SELECT id_leitura, id_medidor, mes_referencia, data_leitura,
                   leitura_anterior, leitura_atual, consumo_kwh,
                   consumo_ano_anterior_kwh, variacao_ano_anterior_pct,
                   tipo_leitura, status_qualidade_leitura, consumo_imputado
            FROM fact_leituras
            WHERE id_uc = :uc_id
            ORDER BY competencia DESC, id_leitura DESC
            LIMIT :limite OFFSET :offset
            """
        )
        try:
            total = self.connection.execute(count_query, {"uc_id": uc_id}).scalar_one()
            if offset >= total:
                return total, []
            rows = (
                self.connection.execute(
                    page_query, {"uc_id": uc_id, "limite": limite, "offset": offset}
                )
                .mappings()
                .all()
            )
        except (InterfaceError, OperationalError, TimeoutError) as exc:
            raise GoldUnavailableError("Gold indisponível") from exc
        return total, [dict(row) for row in rows]

    def get_faturas_em_aberto(self, uc_id: str) -> list[dict[str, object]]:
        """Consulta faturas abertas segundo o status já publicado pela Gold."""
        query = text(
            """
            SELECT id_fatura, mes_referencia, data_vencimento,
                   receita_faturada, status_pagamento
            FROM fact_faturamento
            WHERE id_uc = :uc_id
              AND status_pagamento IN ('PENDENTE', 'ATRASADA')
            ORDER BY data_vencimento ASC, id_fatura ASC
            """
        )
        try:
            rows = self.connection.execute(query, {"uc_id": uc_id}).mappings().all()
        except (InterfaceError, OperationalError, TimeoutError) as exc:
            raise GoldUnavailableError("Gold indisponível") from exc
        return [dict(row) for row in rows]

    def get_faturas_page(
        self, uc_id: str, limite: int, offset: int
    ) -> tuple[int, list[dict[str, object]]]:
        """Conta e consulta uma página do histórico de faturas da UC."""
        count_query = text("SELECT count(*) FROM fact_faturamento WHERE id_uc = :uc_id")
        page_query = text(
            """
            SELECT id_fatura, mes_referencia, consumo_kwh, bandeira_tarifaria,
                   receita_faturada, data_vencimento, status_pagamento,
                   data_emissao, data_pagamento, dias_atraso
            FROM fact_faturamento
            WHERE id_uc = :uc_id
            ORDER BY competencia DESC, id_fatura DESC
            LIMIT :limite OFFSET :offset
            """
        )
        try:
            total = self.connection.execute(count_query, {"uc_id": uc_id}).scalar_one()
            if offset >= total:
                return total, []
            rows = (
                self.connection.execute(
                    page_query, {"uc_id": uc_id, "limite": limite, "offset": offset}
                )
                .mappings()
                .all()
            )
        except (InterfaceError, OperationalError, TimeoutError) as exc:
            raise GoldUnavailableError("Gold indisponível") from exc
        return total, [dict(row) for row in rows]

    def get_resumo_faturas_em_aberto(self, uc_id: str) -> tuple[int, float | None]:
        """Conta e soma faturas abertas sem substituir nulos por zero."""
        query = text(
            """
            SELECT count(*) AS quantidade, sum(receita_faturada) AS valor_total
            FROM fact_faturamento
            WHERE id_uc = :uc_id
              AND status_pagamento IN ('PENDENTE', 'ATRASADA')
            """
        )
        try:
            row = self.connection.execute(query, {"uc_id": uc_id}).one()
        except (InterfaceError, OperationalError, TimeoutError) as exc:
            raise GoldUnavailableError("Gold indisponível") from exc
        return row.quantidade, row.valor_total

    def get_interrupcoes_page(
        self, uc_id: str, limite: int, offset: int
    ) -> tuple[int, list[dict[str, object]]]:
        """Conta e pagina interrupções registradas para a UC na Gold."""
        count_query = text("SELECT count(*) FROM fact_ocorrencias WHERE id_uc = :uc_id")
        page_query = text(
            """
            SELECT id_ocorrencia, alimentador, tipo, causa, data_abertura,
                   data_encerramento, duracao_h, duracao_truncada
            FROM fact_ocorrencias
            WHERE id_uc = :uc_id
            ORDER BY data_abertura DESC, id_ocorrencia DESC
            LIMIT :limite OFFSET :offset
            """
        )
        try:
            total = self.connection.execute(count_query, {"uc_id": uc_id}).scalar_one()
            if offset >= total:
                return total, []
            rows = (
                self.connection.execute(
                    page_query, {"uc_id": uc_id, "limite": limite, "offset": offset}
                )
                .mappings()
                .all()
            )
        except (InterfaceError, OperationalError, TimeoutError) as exc:
            raise GoldUnavailableError("Gold indisponível") from exc
        return total, [dict(row) for row in rows]

    def get_chamados_page(
        self, uc_id: str, limite: int, offset: int
    ) -> tuple[int, list[dict[str, object]]]:
        """Conta e pagina chamados registrados para a UC na Gold."""
        count_query = text(
            "SELECT count(*) FROM fact_atendimentos WHERE id_uc = :uc_id"
        )
        page_query = text(
            """
            SELECT protocolo, assunto, subassunto, canal, data_abertura,
                   data_fechamento, status_chamado, qtd_tratativas
            FROM fact_atendimentos
            WHERE id_uc = :uc_id
            ORDER BY data_abertura DESC, protocolo DESC
            LIMIT :limite OFFSET :offset
            """
        )
        try:
            total = self.connection.execute(count_query, {"uc_id": uc_id}).scalar_one()
            if offset >= total:
                return total, []
            rows = (
                self.connection.execute(
                    page_query, {"uc_id": uc_id, "limite": limite, "offset": offset}
                )
                .mappings()
                .all()
            )
        except (InterfaceError, OperationalError, TimeoutError) as exc:
            raise GoldUnavailableError("Gold indisponível") from exc
        return total, [dict(row) for row in rows]
