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
from typing import Any, Dict, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "src.grafo"

from ..contratos.resposta_agente import RespostaAgente
from .construtor_grafo import construir_grafo_final
from ..interfaces.validador_sql_interface import ValidadorSQLInterface
from ..provedores.cliente_llm import ClienteLLM
from ..services.sql_executor import SQLExecutor
from ..services.tela_dashboard import tela_do_dashboard

logger = logging.getLogger("venergy.executor_agente")

# Só resposta com consulta executada leva o portal para uma tela
_SELOS_COM_DADOS = {"certificada", "gerada_confiavel"}

# Selos que indicam resposta baseada em dados (exigem SQL)
_SELOS_BASEADOS_EM_DADOS = {"certificada", "gerada_confiavel"}


def avaliar_resultado_teste_pipeline(resposta: RespostaAgente) -> tuple[int, str]:
    """
    Avalia o resultado do script de teste manual (_testar_pipeline_com_banco).
    Não imprime nada; retorna (código_de_saída, mensagem).
    Regras, nesta ordem:
    - selo == "erro_bloqueado" -> (1, "Falha: o pipeline não conseguiu concluir a execução.")
    - selo == "recusa_honesta" -> (0, "Aviso: o agente recusou responder (não é erro de execução).")
    - selo em ("certificada", "gerada_confiavel") e not resposta.sql_gerado ->
      (1, "Falha: resposta baseada em dados, mas nenhum SQL foi executado.")
    - selo == "documental_rag" -> (0, "Pipeline concluído com sucesso (resposta documental, sem SQL).")
    - demais casos -> (0, "Pipeline concluído com sucesso.")
    """
    selo = resposta.selo_confianca

    if selo == "erro_bloqueado":
        return 1, "Falha: o pipeline não conseguiu concluir a execução."

    if selo == "recusa_honesta":
        return 0, "Aviso: o agente recusou responder (não é erro de execução)."

    if selo in _SELOS_BASEADOS_EM_DADOS and not resposta.sql_gerado:
        return 1, "Falha: resposta baseada em dados, mas nenhum SQL foi executado."

    if selo == "documental_rag":
        return 0, "Pipeline concluído com sucesso (resposta documental, sem SQL)."

    return 0, "Pipeline concluído com sucesso."


def executar_agente(
    pergunta: str,
    historico: Optional[list[dict]] = None,
    sessao_id: Optional[str] = None,
    llm: Optional[ClienteLLM] = None,
    validador: Optional[ValidadorSQLInterface] = None,
    executor: Optional[SQLExecutor] = None,
    db_url: Optional[str] = None,
    user_id: Optional[str] = None,
    contexto_tela: Optional[Dict[str, Any]] = None,
) -> RespostaAgente:
    """
    Executa o agente V-Energy Grid 360 ponta a ponta e retorna um schema Pydantic estruturado.

    Args:
        pergunta:    Texto da pergunta do usuário em linguagem natural.
        historico:   Lista de turnos anteriores no formato [{"role": "user"/"assistant", "content": "..."}].
        sessao_id:   Identificador único da sessão (gerado automaticamente se None).
        llm:         Cliente LLM (usa padrão com fallback OpenRouter → 9router se None).
        validador:   Validador SQL (usa ValidadorSQLGlotPostgres se None).
        executor:    Executor SQL (usa SQLExecutor padrão se None).
        db_url:      URL de conexão ao PostgreSQL (usa DATABASE_URL do env se None).
        user_id:     Identificador do usuário autenticado (virá da autenticação no futuro).
        contexto_tela: Contexto da tela aberta no portal (page, id_uc, etc.).

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
        user_id=user_id,
        contexto_tela=contexto_tela,
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
    selo = estado_final.get("selo_confianca", "erro_bloqueado")
    dashboard = (
        tela_do_dashboard(estado_final.get("sql_gerado"), dados_brutos)
        if selo in _SELOS_COM_DADOS
        else None
    )
    return RespostaAgente(
        audit_id=estado_final.get("audit_id", str(uuid.uuid4())),
        pergunta_original=estado_final.get("pergunta_original", pergunta),
        pergunta_autonoma=estado_final.get("pergunta_autonoma", pergunta),
        resposta_texto=estado_final.get("texto_resposta", ""),
        sql_gerado=estado_final.get("sql_gerado"),
        dados_tabela=dados_brutos,
        selo_confianca=selo,
        fontes_citadas=estado_final.get("fontes_citadas", []),
        passos_executados=estado_final.get("passos_executados", []),
        hit_cache=estado_final.get("hit_cache", False),
        tempo_execucao_ms=estado_final.get("tempo_total_ms", 0.0),
        tokens_totais=(
            estado_final.get("tokens_prompt", 0) + estado_final.get("tokens_resposta", 0)
        ),
        chamadas_llm=estado_final.get("chamadas_llm", 0),
        dashboard=dashboard,
    )


def _testar_pipeline_com_banco() -> int:
    """Executa uma pergunta real no grafo usando a conexão configurada no .env.

    Uso: python -m src.grafo.executor_agente "sua pergunta aqui"
    Se nenhuma pergunta for passada, usa a padrão.
    """
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

    pergunta = " ".join(sys.argv[1:]).strip() or (
        " qual o KWh médio no Cabo de Santo Agostinho na classe industrial "
        
    )
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
    if resposta.fontes_citadas:
        print(f"Fontes: {resposta.fontes_citadas}")

    codigo, mensagem = avaliar_resultado_teste_pipeline(resposta)
    print(f"\n{mensagem}")
    return codigo


if __name__ == "__main__":
    sys.exit(_testar_pipeline_com_banco())
