"""DTOs dos cartões cadastrais da Visão 360."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class UCIdentification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_uc: str
    nome_titular: str | None
    logradouro: str | None
    numero: str | None
    bairro: str | None
    municipio: str | None
    uf: str | None
    classe: str | None


class CurrentMeter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_medidor_atual: str
    tipo_medidor_atual: str | None
    modelo_medidor_atual: str | None
    data_instalacao_medidor_atual: date | None


class DistributedGeneration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    possui_gd: bool | None
    data_conexao_gd: date | None
    potencia_gd_kwp: float | None
    modalidade_gd: str | None


class UCCadastro(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uc: UCIdentification
    medidor_atual: CurrentMeter | None
    geracao_distribuida: DistributedGeneration


class ConsumptionMonth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mes_referencia: str
    consumo_kwh: float | None
    consumo_ano_anterior_kwh: float | None
    variacao_ano_anterior_pct: float | None


class ReadingItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_leitura: str
    id_medidor: str | None
    mes_referencia: str
    data_leitura: date | None
    leitura_anterior: float | None
    leitura_atual: float | None
    consumo_kwh: float | None
    consumo_ano_anterior_kwh: float | None
    variacao_ano_anterior_pct: float | None
    tipo_leitura: str | None
    status_qualidade_leitura: str | None
    consumo_imputado: bool | None


class PaginatedReadings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pagina: int
    limite: int
    total: int
    itens: list[ReadingItem]


class ReadingHistory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    leituras: PaginatedReadings


class UCConsumptionReadings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consumo_12m: list[ConsumptionMonth]
    historicos: ReadingHistory


class OpenInvoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_fatura: str
    mes_referencia: str
    data_vencimento: date | None
    receita_faturada: float | None
    status_pagamento: str | None


class InvoiceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_fatura: str
    mes_referencia: str
    consumo_kwh: float | None
    bandeira_tarifaria: str | None
    receita_faturada: float | None
    data_vencimento: date | None
    status_pagamento: str | None
    data_emissao: date | None
    data_pagamento: date | None
    dias_atraso: int | None


class PaginatedInvoices(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pagina: int
    limite: int
    total: int
    itens: list[InvoiceItem]


class InvoiceHistory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    faturas: PaginatedInvoices


class UCInvoices(BaseModel):
    model_config = ConfigDict(extra="forbid")

    faturas_em_aberto: list[OpenInvoice]
    historicos: InvoiceHistory


class InterruptionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_ocorrencia: str
    alimentador: str | None
    tipo: str | None
    causa: str | None
    data_abertura: datetime | None
    data_encerramento: datetime | None
    duracao_h: float | None
    duracao_truncada: bool | None


class CallItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocolo: str
    assunto: str | None
    subassunto: str | None
    canal: str | None
    data_abertura: datetime | None
    data_fechamento: datetime | None
    status_chamado: str | None
    qtd_tratativas: int | None


class PaginatedInterruptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pagina: int
    limite: int
    total: int
    itens: list[InterruptionItem]


class PaginatedCalls(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pagina: int
    limite: int
    total: int
    itens: list[CallItem]


class OperationalHistory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interrupcoes: PaginatedInterruptions
    chamados: PaginatedCalls


class UCOperationalHistories(BaseModel):
    model_config = ConfigDict(extra="forbid")

    historicos: OperationalHistory


class OpenInvoiceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantidade: int
    valor_total: float | None


class UCHistory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    faturas: PaginatedInvoices
    interrupcoes: PaginatedInterruptions
    chamados: PaginatedCalls
    leituras: PaginatedReadings


class UC360Response(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uc: UCIdentification
    medidor_atual: CurrentMeter | None
    geracao_distribuida: DistributedGeneration
    faturas_em_aberto: list[OpenInvoice]
    resumo_faturas_em_aberto: OpenInvoiceSummary
    consumo_12m: list[ConsumptionMonth]
    historicos: UCHistory
