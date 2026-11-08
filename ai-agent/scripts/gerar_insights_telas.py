"""Renova os quatro insights globais após a carga Gold ou antes da apresentação.

Na pasta ai-agent: python -m scripts.gerar_insights_telas
Remove somente cada par (tela, 'global'). Fallback não é persistido: rode novamente.
"""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

from src.insights.service import InsightsService
from src.provedores.cliente_llm import ClienteLLM

TELAS_GLOBAIS = ("receita", "indicadores", "continuidade", "fila_inspecao")
RAIZ = Path(__file__).resolve().parents[2]


def renovar_insights(service: InsightsService) -> bool:
    """Retorna sucesso somente quando todos os textos auditados estão no cache."""
    sucesso = True
    for tela in TELAS_GLOBAIS:
        try:
            with psycopg2.connect(service.db_url, connect_timeout=5) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM tb_insights_tela WHERE tela = %s AND entidade_id = %s",
                        (tela, "global"),
                    )
            resultado = service.obter(tela, "global")
            print(f"{tela} | {resultado['selo']} | {resultado['insight_texto']}")
            if resultado["selo"] != "auditado_llm":
                sucesso = False
                print(f"{tela}: fallback não gravado; execute novamente.")
            elif service._ler_cache(tela, "global") is None:
                sucesso = False
                print(f"{tela}: texto gerado, mas a persistência no cache não foi confirmada.")
        except Exception:
            # Erros de conexão podem incluir credenciais: não imprimir a exceção.
            sucesso = False
            print(f"{tela}: falha ao renovar insight; verifique banco e provedor LLM.")
    return sucesso


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    load_dotenv(RAIZ / "backend" / ".env.local")
    load_dotenv(RAIZ / ".env")
    db_url = os.getenv("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://", 1)
    if not db_url:
        print("DATABASE_URL não definida no ambiente ou backend/.env.local.")
        return 1
    cliente = ClienteLLM()
    if cliente.forcar_mock or not (cliente.openrouter_key or cliente.ninerouter_key):
        print("Configure um provedor LLM real e desative LLM_MOCK_MODE antes de gerar o cache.")
        return 1
    # O serviço e o executor registram exceções de conexão; este comando exibe
    # apenas os resultados e erros seguros acima, sem URL do banco nos logs.
    nivel_anterior = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        return 0 if renovar_insights(InsightsService(llm=cliente, db_url=db_url)) else 1
    finally:
        logging.disable(nivel_anterior)


if __name__ == "__main__":
    raise SystemExit(main())
