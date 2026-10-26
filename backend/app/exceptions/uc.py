"""Falhas semânticas da consulta cadastral da UC."""


class InvalidUCIdError(ValueError):
    """O identificador informado não segue o formato da Gold."""


class InvalidPaginationError(ValueError):
    """A página ou o limite não segue o contrato da Visão 360."""


class UCNotFoundError(LookupError):
    """Não há UC para o identificador válido informado."""


class GoldUnavailableError(RuntimeError):
    """A consulta à Gold falhou por indisponibilidade ou timeout."""
