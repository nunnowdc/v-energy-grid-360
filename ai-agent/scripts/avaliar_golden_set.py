#!/usr/bin/env python
"""
Avalia o agente contra o golden set, com o modelo e o banco de verdade, e grava o
resultado para a tela "Avaliação do agente" do Admin TI (REQ-AI-08).

Cada execução faz as perguntas de tests/golden_dataset/golden_dataset.json ao agente
(alguns minutos e algumas centenas de milhares de tokens) e grava uma linha em
tb_avaliacoes_agente, com os casos em tb_avaliacoes_agente_casos. As perguntas não
entram na auditoria, então não aparecem no uso do agente.

Execute, na pasta ai-agent:
  python -m scripts.avaliar_golden_set
  python -m scripts.avaliar_golden_set --sem-gravar   # só mostra o resultado
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
# As chaves do LLM e o banco ficam no backend/.env.local, como para o backend;
# o .env da raiz é só a reserva da DATABASE_URL
load_dotenv(RAIZ / "backend" / ".env.local")
load_dotenv(RAIZ / ".env")
# O ai-agent lê a URL sem o driver, como no backend/app/main.py
if os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["DATABASE_URL"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )

from src.avaliacao.armazenamento import gravar_execucao
from src.avaliacao.golden_set import (
    META_ABSTENCAO,
    META_COMPONENT_MATCH,
    META_EXECUCAO,
    META_TOKENS,
    carregar_casos,
    executar_avaliacao,
)
from src.grafo.executor_agente import executar_agente
from src.provedores.cliente_llm import ClienteLLM


def modelo_usado(cliente: ClienteLLM) -> str | None:
    """O OpenRouter é tentado primeiro; sem a chave dele, quem responde é o 9router."""
    return (
        cliente.modelo_primario if cliente.openrouter_key else cliente.modelo_fallback
    )


def _taxa(valor: float | None) -> str:
    return "—" if valor is None else f"{valor:.1f}%".replace(".", ",")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Avalia o agente contra o golden set.")
    parser.add_argument(
        "--sem-gravar",
        action="store_true",
        help="Só mostra o resultado, sem gravar no banco",
    )
    args = parser.parse_args(argv)

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL não definida no backend/.env.local")
        return 1
    cliente = ClienteLLM()
    if cliente.forcar_mock:
        print("LLM_MOCK_MODE está ligado: a avaliação precisa do modelo de verdade")
        return 1
    if not cliente.openrouter_key and not cliente.ninerouter_key:
        print(
            "Nenhuma chave de LLM no backend/.env.local (OPENROUTER_API_KEY ou NINEROUTER_API_KEY)"
        )
        return 1

    casos = carregar_casos()
    modelo = modelo_usado(cliente)
    print(f"Avaliando {len(casos)} casos do golden set com {modelo}...")

    def mostrar(caso: dict) -> None:
        print(
            f"  {caso['caso_id']}  {'passou' if caso['passou'] else 'FALHOU'}  {caso['motivo']}"
        )

    execucao = executar_avaliacao(
        casos,
        lambda **kwargs: executar_agente(llm=cliente, **kwargs),
        ao_terminar_caso=mostrar,
    )

    print()
    print(
        f"Casos aprovados:        {execucao['casos_aprovados']} de {execucao['total_casos']}"
    )
    print(
        f"Execução das consultas: {_taxa(execucao['taxa_execucao'])} (meta: {META_EXECUCAO:.0f}% ou mais)"
    )
    print(
        f"Tabelas certas (AST):   {_taxa(execucao['taxa_component_match'])} (meta: {META_COMPONENT_MATCH:.0f}% ou mais)"
    )
    print(
        f"Abstenção correta:      {_taxa(execucao['taxa_abstencao'])} (meta: {META_ABSTENCAO:.0f}%)"
    )
    tokens = execucao["tokens_medio"]
    print(
        f"Tokens por pergunta:    {'—' if tokens is None else round(tokens)} (meta: menos de {META_TOKENS:.0f})"
    )
    print(f"Duração:                {execucao['duracao_ms'] / 1000:.0f} s")

    if args.sem_gravar:
        return 0

    import psycopg2

    with psycopg2.connect(db_url) as conexao:
        avaliacao_id = gravar_execucao(conexao, execucao, modelo)
    print(f"\nGravada como {avaliacao_id}. Veja na tela Avaliação do agente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
