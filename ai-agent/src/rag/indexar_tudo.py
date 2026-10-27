"""
Runner unificado para indexar todo o conhecimento no RAG.
Executa ambos os indexadores em sequência:
  1. indexador_conhecimento.py — conhecimento base (glossário, esquema, PRODIST, templates)
  2. indexador_relatorios_eng_dados.py — relatórios técnicos de engenharia de dados

Execute:
  python -m ai_agent.src.rag.indexar_tudo
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
# Raiz do projeto (pasta ai-agent/, que contém src/ e o .env)
RAIZ_PROJETO = Path(__file__).resolve().parents[2]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from dotenv import load_dotenv

load_dotenv(RAIZ_PROJETO / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("venergy.indexar_tudo")


def main():
    logger.info("=" * 60)
    logger.info("INDEXAÇÃO COMPLETA DO RAG - V-ENERGY GRID 360")
    logger.info("=" * 60)

    # 1. Conhecimento base (glossário, esquema, regras setoriais, templates)
    logger.info("\n[1/2] Indexando conhecimento base...")
    try:
        from .indexador_conhecimento import indexar_conhecimento
        indexar_conhecimento()
    except Exception as e:
        logger.error("Erro no indexador de conhecimento base: %s", e)
        sys.exit(1)

    # 2. Relatórios de engenharia de dados
    logger.info("\n[2/2] Indexando relatórios de engenharia de dados...")
    try:
        from .indexador_relatorios_eng_dados import indexar_relatorios_eng_dados
        indexar_relatorios_eng_dados()
    except Exception as e:
        logger.error("Erro no indexador de relatórios: %s", e)
        sys.exit(1)

    logger.info("\n" + "=" * 60)
    logger.info("✅  INDEXAÇÃO COMPLETA CONCLUÍDA COM SUCESSO")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()