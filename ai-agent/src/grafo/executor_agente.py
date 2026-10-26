"""
Ponto de entrada público do Agente V-Energy Grid 360.
Expõe a função executar_agente() consumida pelo FastAPI, pelo CLI e pelo harness de testes.
"""
from __future__ import annotations

import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "src.grafo"

from ..contratos.resposta_agente import RespostaAgente
from .construtor_grafo import construir_grafo_final
from ..interfaces.validador_sql_interface import ValidadorSQLInterface
from ..provedores.cliente_llm import ClienteLLM
from ..services.sql_executor import SQLExecutor

logger = logging.getLogger("venergy.executor_agente")


def executar_agente(
    pergunta: str,
    historico: Optional[list[dict]] = None,
    sessao_id: Optional[str] = None,
    llm: Optional[ClienteLLM] = None,
    validador: Optional[ValidadorSQLInterface] = None,
    executor: Optional[SQLExecutor] = None,
    db_url: Optional[str] = None,
) -> RespostaAgente:
    """
    Executa o agente V-Energy Grid 360 ponta a ponta e retorna um schema Pydantic estruturado.

    Args:
        pergunta:    Texto da pergunta do usuário em linguagem natural.
        historico:   Lista de turnos anteriores no formato [{"role": "user"/"assistant", "content": "..."}].
        sessao_id:   Identificador único da sessão (gerado automaticamente se None).
        llm:         Cliente LLM (usa padrão com fallback OpenRouter → 9router se None).
        validador:   Validador SQL (usa StubValidadorSQL se None).
        executor:    Executor SQL (usa SQLExecutor padrão se None).
        db_url:      URL de conexão ao PostgreSQL (usa DATABASE_URL do env se None).

    Returns:
        RespostaAgente: Contrato padronizado com resposta, SQL, dados, selo e auditoria.
    """
    if not sessao_id:
        sessao_id = str(uuid.uuid4())

    grafo, inicializar = construir_grafo_final(
        llm=llm,
        validador=validador,
        executor=executor,
        db_url=db_url,
    )

    estado_inicial = inicializar(
        pergunta=pergunta,
        historico=historico,
        sessao_id=sessao_id,
    )

    try:
        estado_final = grafo.invoke(estado_inicial)
    except Exception as e:
        logger.error("Falha crítica na execução do grafo: %s", e, exc_info=True)
        return RespostaAgente(
            audit_id=str(uuid.uuid4()),
            pergunta_original=pergunta,
            pergunta_autonoma=pergunta,
            resposta_texto=(
                "Ocorreu um erro interno ao processar sua pergunta. "
                "Nossa equipe técnica foi notificada."
            ),
            sql_gerado=None,
            dados_tabela=None,
            selo_confianca="erro_bloqueado",
            fontes_citadas=[],
            passos_executados=["Erro crítico na execução do grafo."],
            hit_cache=False,
            tempo_execucao_ms=0.0,
            tokens_totais=0,
            chamadas_llm=0,
        )

    # Mapeia o estado final do LangGraph para o contrato de saída público
    dados_brutos = estado_final.get("dados_sql")
    return RespostaAgente(
        audit_id=estado_final.get("audit_id", str(uuid.uuid4())),
        pergunta_original=estado_final.get("pergunta_original", pergunta),
        pergunta_autonoma=estado_final.get("pergunta_autonoma", pergunta),
        resposta_texto=estado_final.get("texto_resposta", ""),
        sql_gerado=estado_final.get("sql_gerado"),
        dados_tabela=dados_brutos,
        selo_confianca=estado_final.get("selo_confianca", "erro_bloqueado"),
        fontes_citadas=estado_final.get("fontes_citadas", []),
        passos_executados=estado_final.get("passos_executados", []),
        hit_cache=estado_final.get("hit_cache", False),
        tempo_execucao_ms=estado_final.get("tempo_total_ms", 0.0),
        tokens_totais=(
            estado_final.get("tokens_prompt", 0) + estado_final.get("tokens_resposta", 0)
        ),
        chamadas_llm=estado_final.get("chamadas_llm", 0),
    )


def _testar_pipeline_com_banco() -> int:
    """Executa uma pergunta real no grafo usando a conexão configurada no .env."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("Erro: instale a dependência python-dotenv.")
        return 1

    raiz_projeto = Path(__file__).resolve().parents[3]
    arquivo_env = raiz_projeto / ".env"
    load_dotenv(arquivo_env)

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print(f"Erro: DATABASE_URL não encontrada em {arquivo_env}.")
        return 1

    pergunta = "Qual foi o faturamento total de Recife em 2023?."
    print(f"Arquivo .env: {arquivo_env}")
    print(f"Pergunta de teste: {pergunta}")
    print("Executando o pipeline do agente...")

    resposta = executar_agente(pergunta=pergunta, db_url=db_url)

    print("\nResultado do pipeline:")
    print(f"Selo de confiança: {resposta.selo_confianca}")
    print(f"Resposta: {resposta.resposta_texto}")
    print(f"SQL executado: {resposta.sql_gerado}")
    print(f"Dados retornados: {resposta.dados_tabela}")
    print(f"Passos: {resposta.passos_executados}")
    print(f"Chamadas ao LLM: {resposta.chamadas_llm}")

    if resposta.selo_confianca == "erro_bloqueado":
        print("\nFalha: o pipeline não conseguiu concluir a execução.")
        return 1

    if not resposta.sql_gerado:
        print("\nFalha: o pipeline não gerou nem executou SQL.")
        return 1

    print("\nPipeline concluído com sucesso.")
    return 0


if __name__ == "__main__":
    sys.exit(_testar_pipeline_com_banco())
