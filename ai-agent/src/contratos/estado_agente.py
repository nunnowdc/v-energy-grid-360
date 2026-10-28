"""
Contratos de Estado e Tipagem para o Grafo LangGraph do Agente V-Energy Grid 360.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict
from pydantic import BaseModel, Field

CategoriaDocumentoContexto = Literal[
    "glossario",
    "esquema",
    "prodist",
    "templates",
    "perfis_dados",
    "dicionario_gold",
    "decisoes_negocio",
    "regras_setoriais",
    "lgpd",
    "outros_relatorios",
]


class DocumentoContexto(BaseModel):
    """Representa um fragmento de documento ou esquema recuperado pelo RAG."""
    id: str
    categoria: CategoriaDocumentoContexto
    titulo: str
    conteudo: str
    fonte: str
    similaridade: float = 1.0


class EstadoAgente(TypedDict, total=False):
    """
    Estado compartilhado que transita entre todos os nós do LangGraph.
    """
    # Identificação da Sessão e Usuário
    sessao_id: str
    user_id: Optional[str]
    perfil: Optional[str]
    
    # Entradas do Usuário
    pergunta_original: str
    historico_recente: List[Dict[str, str]]
    contexto_tela: Optional[Dict[str, Any]]
    
    # Processamento Conversacional e Escopo
    pergunta_autonoma: str
    dentro_escopo: bool
    motivo_fora_escopo: Optional[str]
    
    # Roteamento
    rota: Literal["sql", "rag", "ambos", "recusa", "fora_escopo", "bloqueio_seguranca"]
    motivo_rota: Optional[str]
    confianca_rota: float
    
    # RAG e Conhecimento
    contexto_rag: List[Dict[str, Any]]
    
    # Cache
    hit_cache: bool
    sql_cache: Optional[str]
    parametros_cache: Optional[Dict[str, Any]]
    
    # Text-to-SQL e Validação
    sql_gerado: Optional[str]
    premissas_sql: Optional[List[str]]
    tentativas_sql: int
    max_tentativas: int
    erro_validacao_ou_execucao: Optional[str]
    malicioso: bool
    
    # Execução de Dados
    dados_sql: Optional[List[Dict[str, Any]]]
    total_linhas_retornadas: int
    tempo_execucao_sql_ms: float
    
    # Síntese e Fechamento
    texto_resposta: str
    fontes_citadas: List[str]
    motivo_recusa: Optional[str]
    selo_confianca: Literal[
        "certificada", 
        "gerada_confiavel", 
        "documental_rag", 
        "recusa_honesta", 
        "erro_bloqueado"
    ]
    
    # Auditoria e FinOps (Passos são acumulados via operator.add)
    passos_executados: Annotated[List[str], operator.add]
    tokens_prompt: int
    tokens_resposta: int
    chamadas_llm: int
    tempo_inicio_ts: float
    tempo_total_ms: float
    audit_id: Optional[str]
