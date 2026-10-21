"""
Contrato final de resposta devolvido pelo Agente para o Portal Web e para o Harness de Testes.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class RespostaAgente(BaseModel):
    """
    Estrutura de dados pública padronizada para retorno do agente.
    Permite testes automatizados desacoplados e consumo direto pelo FastAPI.
    """
    audit_id: str = Field(description="UUID único da execução gravado na auditoria.")
    pergunta_original: str = Field(description="Texto bruto enviado pelo usuário.")
    pergunta_autonoma: str = Field(description="Pergunta após desambiguação de contexto/follow-up.")
    resposta_texto: str = Field(description="Narrativa clara gerada para o usuário.")
    sql_gerado: Optional[str] = Field(default=None, description="Consulta SQL executada no banco, se aplicável.")
    dados_tabela: Optional[List[Dict[str, Any]]] = Field(default=None, description="Amostra dos dados retornados pelo SQL.")
    selo_confianca: Literal[
        "certificada", 
        "gerada_confiavel", 
        "documental_rag", 
        "recusa_honesta", 
        "erro_bloqueado"
    ] = Field(description="Classificação de confiabilidade da resposta.")
    fontes_citadas: List[str] = Field(default_factory=list, description="Lista de normas ou tabelas que fundamentam a resposta.")
    passos_executados: List[str] = Field(default_factory=list, description="Linha do tempo de nós e decisões no LangGraph.")
    hit_cache: bool = Field(default=False, description="Indica se a resposta veio de template de cache certificado.")
    tempo_execucao_ms: float = Field(default=0.0, description="Latência total da requisição em milissegundos.")
    tokens_totais: int = Field(default=0, description="Total de tokens consumidos na interação.")
    chamadas_llm: int = Field(default=0, description="Quantidade de chamadas a provedores de LLM realizadas.")
