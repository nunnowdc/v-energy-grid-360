"""
Indexador de Relatórios de Engenharia de Dados — popula a base vetorial (tb_conhecimento_vetorial)
com conhecimento extraído dos relatórios técnicos em data-engineering/relatorio_tabelas/.

Categorias indexadas:
  - dicionario_gold: definições de tabelas, colunas, métricas, regras de decisão por tabela
  - decisoes_negocio: decisões de modelagem, regras regulatórias, decomposições, metodologias
  - lgpd: classificação de risco, mapa de dados pessoais, recomendações de governança
  - perfis_dados: problemas de qualidade, tratamentos propostos, pendências por fonte

Execute direto no VS Code (F5 / Run Python File) ou terminal:
  python ai_agent/src/rag/indexador_relatorios_eng_dados.py
  python -m ai_agent.src.rag.indexador_relatorios_eng_dados
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2
from dotenv import load_dotenv

# Garante que a raiz do projeto esteja no sys.path para imports absolutos funcionarem
# quando rodado direto como script (python arquivo.py)
ROOT = Path(__file__).resolve().parents[3]  # c:\VScode\v-energy-grid-360
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv()

logger = logging.getLogger("venergy.indexador_relatorios_eng_dados")

# ── Configuração ──────────────────────────────────────────────────────────────
RELATORIOS_DIR = Path(__file__).resolve().parents[3] / "data-engineering" / "relatorio_tabelas"

MODELO_EMBEDDING = "paraphrase-multilingual-MiniLM-L12-v2"
DIMENSAO_VETOR = 384

INSERT_SQL = """
INSERT INTO tb_conhecimento_vetorial (id, categoria, titulo, conteudo, fonte, metadados, embedding)
VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::vector)
ON CONFLICT DO NOTHING;
"""


# ── Utilitários de Parsing ────────────────────────────────────────────────────

def _extrair_secoes_markdown(conteudo: str) -> List[Dict[str, Any]]:
    """
    Extrai seções de um arquivo Markdown baseado em headers (##, ###, ####).
    Retorna lista de dicts com: nivel, titulo, conteudo, linha_inicio.
    """
    linhas = conteudo.split("\n")
    secoes = []
    secao_atual = None
    buffer = []

    for i, linha in enumerate(linhas):
        match = re.match(r"^(#{2,4})\s+(.+)$", linha)
        if match:
            # Salva seção anterior
            if secao_atual:
                secao_atual["conteudo"] = "\n".join(buffer).strip()
                secoes.append(secao_atual)
            # Nova seção
            nivel = len(match.group(1))
            titulo = match.group(2).strip()
            secao_atual = {
                "nivel": nivel,
                "titulo": titulo,
                "linha_inicio": i,
                "conteudo": "",
            }
            buffer = []
        else:
            buffer.append(linha)

    # Última seção
    if secao_atual:
        secao_atual["conteudo"] = "\n".join(buffer).strip()
        secoes.append(secao_atual)

    return secoes


def _dividir_em_chunks(texto: str, max_chars: int = 1500, overlap: int = 200) -> List[str]:
    """
    Divide texto longo em chunks com overlap para melhor recuperação.
    """
    if len(texto) <= max_chars:
        return [texto]

    chunks = []
    inicio = 0
    while inicio < len(texto):
        fim = min(inicio + max_chars, len(texto))
        # Tenta cortar em fronteira de frase/parágrafo
        if fim < len(texto):
            # Procura último ponto final, quebra de linha ou vírgula
            for sep in ["\n\n", "\n", ". ", ", "]:
                pos = texto.rfind(sep, inicio, fim)
                if pos > inicio + max_chars // 2:
                    fim = pos + len(sep)
                    break
        chunk = texto[inicio:fim].strip()
        if chunk:
            chunks.append(chunk)
        if fim >= len(texto):
            break  # chegou no fim: sem isso, o loop nunca termina
        inicio = fim - overlap
    return chunks


def _processar_dicionario_gold(caminho: Path) -> List[Dict[str, Any]]:
    """
    Processa dicionario_dados_gold.md — extrai cada tabela como documento,
    e cada coluna como sub-documento para busca granular.
    """
    conteudo = caminho.read_text(encoding="utf-8")
    secoes = _extrair_secoes_markdown(conteudo)

    documentos = []
    tabela_atual = None

    for secao in secoes:
        titulo = secao["titulo"]
        texto = secao["conteudo"]

        # Detecta início de tabela (ex: "## agg_continuidade_alimentador")
        match_tabela = re.match(r"^([a-z_]+)\s*$", titulo.lower())
        if match_tabela and secao["nivel"] == 2:
            tabela_atual = match_tabela.group(1)
            # Documento da tabela inteira (resumo)
            documentos.append({
                "categoria": "dicionario_gold",
                "titulo": f"Tabela Gold: {tabela_atual}",
                "conteudo": f"Definição da tabela {tabela_atual} na camada Gold.\n{texto[:2000]}",
                "fonte": "Dicionário de Dados Gold (gerado por 07_dicionario_gold)",
                "metadados": {"tabela": tabela_atual, "tipo": "tabela_resumo"},
            })
            continue

        # Seções de métricas (nível 2 com "Métricas")
        if "métrica" in titulo.lower() or "métricas" in titulo.lower():
            for chunk in _dividir_em_chunks(texto):
                documentos.append({
                    "categoria": "dicionario_gold",
                    "titulo": f"Métricas: {titulo}",
                    "conteudo": chunk,
                    "fonte": "Dicionário de Dados Gold",
                    "metadados": {"tabela": tabela_atual, "tipo": "metricas"},
                })
            continue

        # Colunas individuais (nível 3 dentro de uma tabela)
        if tabela_atual and secao["nivel"] == 3 and "|" in texto:
            # Parse da tabela de colunas em markdown
            linhas_tabela = [l for l in texto.split("\n") if "|" in l and not l.strip().startswith("|---")]
            for linha in linhas_tabela[1:]:  # pula header
                partes = [p.strip() for p in linha.split("|")[1:-1]]
                if len(partes) >= 4:
                    coluna, tipo, descricao = partes[0], partes[1], partes[2]
                    regra = partes[3] if len(partes) > 3 else ""
                    lgpd = partes[4] if len(partes) > 4 else ""

                    doc_texto = f"Coluna {coluna} ({tipo}) na tabela {tabela_atual}: {descricao}. "
                    if regra:
                        doc_texto += f"Regra/decisão: {regra}. "
                    if lgpd:
                        doc_texto += f"Classificação LGPD: {lgpd}."

                    documentos.append({
                        "categoria": "dicionario_gold",
                        "titulo": f"Coluna {tabela_atual}.{coluna}",
                        "conteudo": doc_texto,
                        "fonte": "Dicionário de Dados Gold",
                        "metadados": {
                            "tabela": tabela_atual,
                            "coluna": coluna,
                            "tipo": tipo,
                            "lgpd": lgpd,
                            "tipo_doc": "coluna",
                        },
                    })

    return documentos


def _processar_decisoes_negocio(caminho: Path) -> List[Dict[str, Any]]:
    """
    Processa decisoes_de_negocio_gold.md — extrai cada decisão/modelagem como documento.
    """
    conteudo = caminho.read_text(encoding="utf-8")
    secoes = _extrair_secoes_markdown(conteudo)

    documentos = []

    for secao in secoes:
        titulo = secao["titulo"]
        texto = secao["conteudo"]

        if not texto.strip():
            continue

        # Determina subcategoria baseada no título
        if any(kw in titulo.lower() for kw in ["decisão", "decisoes", "modelagem", "dimensional"]):
            subcategoria = "modelagem"
        elif any(kw in titulo.lower() for kw in ["reconciliação", "fatos", "fact_"]):
            subcategoria = "fatos_reconciliacao"
        elif any(kw in titulo.lower() for kw in ["continuidade", "dec", "fec", "qualidade"]):
            subcategoria = "continuidade"
        elif any(kw in titulo.lower() for kw in ["receita", "preço", "volume", "decomposição", "diagnóstico"]):
            subcategoria = "receita_diagnostico"
        elif any(kw in titulo.lower() for kw in ["perdas", "fila", "inspeção", "score", "fraude"]):
            subcategoria = "perdas_nao_tecnicas"
        elif any(kw in titulo.lower() for kw in ["matriz", "rastreabilidade", "problema"]):
            subcategoria = "rastreabilidade"
        else:
            subcategoria = "geral"

        for chunk in _dividir_em_chunks(texto):
            documentos.append({
                "categoria": "decisoes_negocio",
                "titulo": f"{titulo}",
                "conteudo": chunk,
                "fonte": "Decisões de Negócio e Arquitetura - Camada Gold",
                "metadados": {"subcategoria": subcategoria, "tipo_doc": "decisao"},
            })

    return documentos


def _processar_lgpd(caminho: Path) -> List[Dict[str, Any]]:
    """
    Processa levantamento_lgpd.md — extrai mapa de risco, tabelas, recomendações.
    """
    conteudo = caminho.read_text(encoding="utf-8")
    secoes = _extrair_secoes_markdown(conteudo)

    documentos = []

    for secao in secoes:
        titulo = secao["titulo"]
        texto = secao["conteudo"]

        if not texto.strip():
            continue

        # Identifica tipo de conteúdo
        if "mapa por tabela" in titulo.lower() or "tabela" in titulo.lower():
            subcategoria = "mapa_risco_tabelas"
        elif "risco" in titulo.lower() or "cenário" in titulo.lower():
            subcategoria = "riscos_vazamento"
        elif "medida" in titulo.lower() or "implementada" in titulo.lower():
            subcategoria = "medidas_implementadas"
        elif "recomendação" in titulo.lower() or "obrigatório" in titulo.lower() or "agente" in titulo.lower() or "portal" in titulo.lower():
            subcategoria = "recomendacoes"
        elif "resumo" in titulo.lower() or "apresentação" in titulo.lower():
            subcategoria = "resumo_apresentacao"
        else:
            subcategoria = "geral"

        for chunk in _dividir_em_chunks(texto):
            documentos.append({
                "categoria": "lgpd",
                "titulo": f"LGPD: {titulo}",
                "conteudo": chunk,
                "fonte": "Levantamento LGPD - Pipeline V-Energy Grid 360",
                "metadados": {"subcategoria": subcategoria, "tipo_doc": "lgpd"},
            })

    return documentos


def _processar_perfil(caminho: Path) -> List[Dict[str, Any]]:
    """
    Processa arquivos perfil_*.md — extrai problemas, tratamentos, pendências.
    """
    nome_arquivo = caminho.stem.replace("perfil_", "")
    conteudo = caminho.read_text(encoding="utf-8")
    secoes = _extrair_secoes_markdown(conteudo)

    documentos = []

    for secao in secoes:
        titulo = secao["titulo"]
        texto = secao["conteudo"]

        if not texto.strip():
            continue

        if "problema" in titulo.lower() or "encontrado" in titulo.lower():
            subcategoria = "problemas_qualidade"
        elif "tratamento" in titulo.lower() or "proposto" in titulo.lower() or "silver" in titulo.lower():
            subcategoria = "tratamento_silver"
        elif "pendência" in titulo.lower() or "pendencias" in titulo.lower():
            subcategoria = "pendencias"
        elif "visão geral" in titulo.lower() or "visao geral" in titulo.lower() or "resumo" in titulo.lower():
            subcategoria = "visao_geral"
        else:
            subcategoria = "geral"

        for chunk in _dividir_em_chunks(texto):
            documentos.append({
                "categoria": "perfis_dados",
                "titulo": f"Perfil {nome_arquivo}: {titulo}",
                "conteudo": chunk,
                "fonte": f"Perfil de Dados - {nome_arquivo}",
                "metadados": {"fonte_perfil": nome_arquivo, "subcategoria": subcategoria, "tipo_doc": "perfil"},
            })

    return documentos


def _processar_outros_relatorios(caminho: Path) -> List[Dict[str, Any]]:
    """
    Processa outros relatórios (registro_de_problemas, pendencia_historico_atendimentos).
    """
    conteudo = caminho.read_text(encoding="utf-8")
    secoes = _extrair_secoes_markdown(conteudo)

    documentos = []
    nome_base = caminho.stem

    for secao in secoes:
        titulo = secao["titulo"]
        texto = secao["conteudo"]

        if not texto.strip():
            continue

        for chunk in _dividir_em_chunks(texto):
            documentos.append({
                "categoria": "outros_relatorios",
                "titulo": f"{nome_base}: {titulo}",
                "conteudo": chunk,
                "fonte": f"Relatório Engenharia de Dados - {nome_base}",
                "metadados": {"relatorio": nome_base, "tipo_doc": "relatorio_tecnico"},
            })

    return documentos


# ── Indexação Principal ───────────────────────────────────────────────────────

def _gerar_embedding(texto: str, modelo) -> List[float]:
    vetor = modelo.encode(texto, normalize_embeddings=True)
    return vetor.tolist()


def _embedding_para_pg(vetor: List[float]) -> str:
    return f"[{','.join(str(v) for v in vetor)}]"


def indexar_relatorios_eng_dados(db_url: Optional[str] = None) -> None:
    """
    Popula a base vetorial com conhecimento dos relatórios de engenharia de dados.
    Idempotente: usa ON CONFLICT DO NOTHING.
    """
    db_url = db_url or os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL não definida.")
        sys.exit(1)

    if not RELATORIOS_DIR.exists():
        logger.error("Diretório não encontrado: %s", RELATORIOS_DIR)
        sys.exit(1)

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.error("Instale sentence-transformers: pip install sentence-transformers")
        sys.exit(1)

    logger.info("Carregando modelo de embedding: %s", MODELO_EMBEDDING)
    modelo = SentenceTransformer(MODELO_EMBEDDING)

    # Mapeia arquivos para processadores
    processadores = {
        "dicionario_dados_gold.md": _processar_dicionario_gold,
        "decisoes_de_negocio_gold.md": _processar_decisoes_negocio,
        "levantamento_lgpd.md": _processar_lgpd,
        "perfil_unidades_consumidoras.md": _processar_perfil,
        "perfil_leituras.md": _processar_perfil,
        "perfil_faturas.md": _processar_perfil,
        "perfil_atendimentos.md": _processar_perfil,
        "perfil_ocorrencias_rede.md": _processar_perfil,
        "perfil_medidores.md": _processar_perfil,
        "perfil_geracao_distribuida.md": _processar_perfil,
        "perfil_inspecoes.md": _processar_perfil,
        "registro_de_problemas.md": _processar_outros_relatorios,
        "pendencia_historico_atendimentos.md": _processar_outros_relatorios,
    }

    todos_documentos = []

    for arquivo, processador in processadores.items():
        caminho = RELATORIOS_DIR / arquivo
        if not caminho.exists():
            logger.warning("Arquivo não encontrado: %s", arquivo)
            continue

        logger.info("Processando: %s", arquivo)
        docs = processador(caminho)
        logger.info("  → %d documentos extraídos", len(docs))
        todos_documentos.extend(docs)

    logger.info("Total de documentos para indexar: %d", len(todos_documentos))

    # Indexação no PostgreSQL
    total_inseridos = 0
    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                for doc in todos_documentos:
                    texto_para_embed = f"{doc['titulo']}. {doc['conteudo']}"
                    embedding = _gerar_embedding(texto_para_embed, modelo)

                    cur.execute(INSERT_SQL, (
                        str(uuid.uuid4()),
                        doc["categoria"],
                        doc["titulo"],
                        doc["conteudo"],
                        doc["fonte"],
                        json.dumps(doc["metadados"], ensure_ascii=False),  # JSONB
                        _embedding_para_pg(embedding),
                    ))
                    total_inseridos += 1
            conn.commit()

    except Exception as e:
        logger.error("Erro ao indexar no PostgreSQL: %s", e)
        sys.exit(1)

    logger.info("✅  Indexação de relatórios de engenharia de dados concluída. Total: %d documentos.", total_inseridos)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    indexar_relatorios_eng_dados()