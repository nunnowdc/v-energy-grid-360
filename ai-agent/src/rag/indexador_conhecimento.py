"""
Indexador de Conhecimento — popula a base vetorial (tb_conhecimento_vetorial) com:
  1. Glossário de termos coloquiais → técnicos da V-Energy
  2. Esquema e descrição das colunas da camada Gold
  3. Regras setoriais: PRODIST Módulo 8, Bandeiras Tarifárias, Geração Distribuída
  4. Templates SQL analíticos pré-aprovados

Execute direto no VS Code (F5 / Run Python File) ou terminal:
  python ai_agent/src/rag/indexador_conhecimento.py
  python -m ai_agent.src.rag.indexador_conhecimento
"""
from __future__ import annotations

import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# Garante que a raiz do projeto esteja no sys.path para imports absolutos funcionarem
# quando rodado direto como script (python arquivo.py)
ROOT = Path(__file__).resolve().parents[3]  # c:\VScode\v-energy-grid-360
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv()
logger = logging.getLogger("venergy.indexador_conhecimento")

# ── Conteúdo a ser indexado ───────────────────────────────────────────────────

GLOSSARIO: List[Dict[str, Any]] = [
    {"titulo": "conta de luz", "conteudo": "Corresponde à fatura de energia elétrica emitida mensalmente pela V-Energy. Os dados estão em fact_faturamento (receita_faturada, data_vencimento, status_pagamento).", "fonte": "Glossário V-Energy"},
    {"titulo": "falta de luz / queda de energia", "conteudo": "Evento de interrupção no fornecimento de energia. Registrado em fact_ocorrencias com campos: data_abertura, data_encerramento, duracao_min, duracao_h, causa, alimentador.", "fonte": "Glossário V-Energy"},
    {"titulo": "gato / desvio de energia / fraude", "conteudo": "Ligação clandestina ou adulteração de medidor. Identificada em fact_inspecoes. Causa perda não técnica de receita.", "fonte": "Glossário V-Energy"},
    {"titulo": "relógio / medidor", "conteudo": "Equipamento de medição de consumo elétrico (medidor) da UC. Dados de leitura em fact_leituras (leitura_anterior, leitura_atual, consumo_kwh, tipo_leitura).", "fonte": "Glossário V-Energy"},
    {"titulo": "UC / unidade consumidora", "conteudo": "Unidade consumidora: conjunto de instalações e equipamentos de um cliente conectado à rede. Cadastro em dim_unidade_consumidora (id_uc, municipio, bairro, classe, subgrupo_tarifario, alimentador).", "fonte": "Glossário V-Energy"},
    {"titulo": "inadimplência", "conteudo": "UC com fatura(s) em status_pagamento 'ATRASADA' na tabela fact_faturamento. Filtro: WHERE status_pagamento = 'ATRASADA'.", "fonte": "Glossário V-Energy"},
    {"titulo": "corte / supressão", "conteudo": "Desligamento do fornecimento por falta de pagamento. Evento registrado em fact_atendimentos com motivo_contato contendo 'Corte' ou 'Supressão'.", "fonte": "Glossário V-Energy"},
    {"titulo": "religação", "conteudo": "Reativação do fornecimento após pagamento em atraso. Registrada em fact_atendimentos (motivo_contato = 'Religação').", "fonte": "Glossário V-Energy"},
    {"titulo": "bandeira / bandeira tarifária", "conteudo": "Sinal de custo adicional na conta de luz. Definido pela ANEEL conforme condições hídricas do sistema. Valores em fact_faturamento (bandeira_tarifaria, valor_bandeira). Verde: sem adicional. Amarela: R$ 0,01874/kWh. Vermelha 1: R$ 0,03971/kWh. Vermelha 2: R$ 0,09492/kWh.", "fonte": "ANEEL / Glossário V-Energy"},
    {"titulo": "GD / geração distribuída / solar", "conteudo": "Microgeração ou minigeração de energia elétrica pelo próprio consumidor (ex.: painéis solares). UC marcada com possui_gd = TRUE em dim_unidade_consumidora. A dimensão dim_geracao_distribuida detalha potencia_kwp, modalidade e energia_reestimada_kwh.", "fonte": "Lei 14.300/2022 / Glossário V-Energy"},
    {"titulo": "alimentador / circuito", "conteudo": "Trecho de rede de média tensão que distribui energia a um grupo de UCs. Dados em dim_alimentador (alimentador, total_ucs, municipio_principal, regiao). As agregações de continuidade usam a mesma chave alimentador.", "fonte": "Glossário V-Energy"},
    {"titulo": "subgrupo tarifário", "conteudo": "Classificação da UC para fins de tarifação. O campo oficial é subgrupo_tarifario em dim_unidade_consumidora; a classe de consumo inclui RESIDENCIAL, COMERCIAL, INDUSTRIAL, RURAL e PODER_PUBLICO.", "fonte": "ANEEL Resolução 414 / Glossário V-Energy"},
]

ESQUEMA_COLUNAS: List[Dict[str, Any]] = [
    {"titulo": "dim_unidade_consumidora", "conteudo": "Cadastro central das UCs. Colunas: id_uc, nome_titular, municipio, bairro, classe (RESIDENCIAL/COMERCIAL/INDUSTRIAL/RURAL/PODER_PUBLICO), subgrupo_tarifario, alimentador, status, possui_gd, medidor atual e dados de troca.", "fonte": "Dicionário de Dados Gold"},
    {"titulo": "fact_faturamento", "conteudo": "Faturas mensais emitidas por UC. Colunas: id_fatura, id_uc, competencia, ano, mes, receita_faturada, receita_recebida, bandeira_tarifaria, status_pagamento (PAGA/PENDENTE/ATRASADA), dias_atraso, consumo_kwh e preco_medio_kwh.", "fonte": "Dicionário de Dados Gold"},
    {"titulo": "fact_leituras", "conteudo": "Leituras mensais dos medidores. Colunas: id_leitura, id_uc, id_medidor, competencia, ano, mes, leitura_anterior, leitura_atual, consumo_kwh, consumo_kwh_declarado, consumo_imputado, tipo_leitura (REAL/ESTIMADA), status_qualidade_leitura e variacao_ano_anterior_pct.", "fonte": "Dicionário de Dados Gold"},
    {"titulo": "fact_ocorrencias", "conteudo": "Interrupções de fornecimento. Colunas: id_ocorrencia, id_uc, alimentador, tipo, causa, data_abertura, data_encerramento, competencia, duracao_min, duracao_h, dia_critico, duracao_truncada e eh_oscilacao.", "fonte": "Dicionário de Dados Gold"},
    {"titulo": "fact_atendimentos", "conteudo": "Chamados do call center e campo. Colunas: protocolo, id_uc, assunto, subassunto, canal, data_abertura, data_fechamento, competencia, status_chamado, tempo_resolucao_h, nota_satisfacao e qtd_tratativas.", "fonte": "Dicionário de Dados Gold"},
    {"titulo": "fact_inspecoes", "conteudo": "Inspeções de campo. Colunas: id_inspecao, id_uc, data_inspecao, resultado (IRREGULARIDADE_CONFIRMADA/SEM_IRREGULARIDADE), tipo_irregularidade, kwh_recuperado e registro_coerente.", "fonte": "Dicionário de Dados Gold"},
    {"titulo": "agg_receita_mensal", "conteudo": "Receita, volume e preço por competencia, municipio, bairro, classe e possui_gd. Colunas principais: receita_faturada, receita_recebida, consumo_kwh, faturas_atrasadas e preco_medio_kwh.", "fonte": "Dicionário de Dados Gold"},
    {"titulo": "agg_continuidade_alimentador_anual", "conteudo": "DEC, FEC e rankings anuais por alimentador. Colunas principais: dec, fec, rank_dec e rank_impacto_horas_x_uc.", "fonte": "Dicionário de Dados Gold"},
    {"titulo": "fila_inspecao", "conteudo": "Fila priorizada de UCs suspeitas de perdas não técnicas. Colunas principais: prioridade, id_uc, score, motivo_suspeita e kwh_recuperavel_estimado_ano, com atributos de contexto da UC.", "fonte": "Dicionário de Dados Gold"},
]

REGRAS_SETORIAIS: List[Dict[str, Any]] = [
    {"titulo": "Indicador DEC (Duração Equivalente de Continuidade)", "conteudo": "DEC é a duração equivalente de interrupção por UC, em horas. Para consultas prontas, use agg_continuidade_alimentador.dec ou agg_continuidade_alimentador_anual.dec. A origem operacional é fact_ocorrencias, agregada por alimentador.", "fonte": "PRODIST Módulo 8 / ANEEL"},
    {"titulo": "Indicador FEC (Frequência Equivalente de Continuidade)", "conteudo": "FEC é a frequência equivalente de interrupção por UC. Para consultas prontas, use agg_continuidade_alimentador.fec ou agg_continuidade_alimentador_anual.fec. O ranking anual está em rank_dec e rank_impacto_horas_x_uc.", "fonte": "PRODIST Módulo 8 / ANEEL"},
    {"titulo": "Bandeiras Tarifárias ANEEL (adicional por kWh)", "conteudo": "Sistema de sinalização tarifária conforme condições do reservatório hídrico nacional: Verde = R$ 0,00/kWh; Amarela = R$ 0,01874/kWh; Vermelha Patamar 1 = R$ 0,03971/kWh; Vermelha Patamar 2 = R$ 0,09492/kWh. Valores vigentes da resolução ANEEL. Coluna bandeira_tarifaria em fact_faturamento.", "fonte": "ANEEL Resolução Homologatória"},
    {"titulo": "Geração Distribuída e compensação de créditos (Lei 14.300/2022)", "conteudo": "UCs com geração distribuída são identificadas por possui_gd em dim_unidade_consumidora. A dimensão dim_geracao_distribuida detalha potencia_kwp, modalidade e energia_reestimada_kwh; o consumo e a receita estão em fact_leituras e fact_faturamento.", "fonte": "Lei 14.300/2022 / ANEEL"},
    {"titulo": "Perdas técnicas e não técnicas de energia", "conteudo": "Perdas não técnicas incluem desvios, fraudes e erros de medição. Para priorização operacional, use fila_inspecao.score, motivo_suspeita e kwh_recuperavel_estimado_ano; os resultados de campo estão em fact_inspecoes.", "fonte": "PRODIST Módulo 1 / V-Energy"},
    {"titulo": "Decomposição de Receita: Preço versus Volume", "conteudo": "A variação de receita entre dois períodos pode ser decomposta em: (1) Efeito Preço = variação na tarifa × volume base; (2) Efeito Volume = variação no consumo × tarifa base; (3) Efeito Mix = mudança na composição de classes. Metodologia padrão de diagnóstico de receita da distribuidora.", "fonte": "Diagnóstico V-Energy / Metodologia Interna"},
    {"titulo": "Classes de consumo e suas características", "conteudo": "A coluna classe em dim_unidade_consumidora e nas agregações Gold usa RESIDENCIAL, COMERCIAL, INDUSTRIAL, RURAL e PODER_PUBLICO. O subgrupo tarifario é uma coluna separada.", "fonte": "Dicionário de Dados Gold / V-Energy"},
]

TEMPLATES_SQL: List[Dict[str, Any]] = [
    {"titulo": "Receita total por município e ano", "conteudo": "SELECT r.municipio, r.ano, SUM(r.receita_faturada) AS receita_total FROM agg_receita_mensal r GROUP BY r.municipio, r.ano ORDER BY r.ano DESC, receita_total DESC;", "fonte": "Templates SQL Certificados V-Energy"},
    {"titulo": "UCs inadimplentes por município e classe", "conteudo": "SELECT r.municipio, r.classe, SUM(r.faturas_atrasadas) AS total_faturas_atrasadas FROM agg_receita_mensal r GROUP BY r.municipio, r.classe ORDER BY total_faturas_atrasadas DESC;", "fonte": "Templates SQL Certificados V-Energy"},
    {"titulo": "Ranking anual de DEC por alimentador", "conteudo": "SELECT a.alimentador, a.ano, a.municipio_principal, a.dec, a.fec, a.rank_dec, a.rank_impacto_horas_x_uc FROM agg_continuidade_alimentador_anual a WHERE a.ano = :ano ORDER BY a.rank_dec;", "fonte": "Templates SQL Certificados V-Energy / PRODIST Módulo 8"},
    {"titulo": "Impacto da bandeira tarifária na receita mensal", "conteudo": "SELECT r.competencia, r.bandeira_tarifaria, SUM(r.receita_faturada) AS receita_total, SUM(r.receita_energia) AS receita_energia FROM agg_receita_mensal r WHERE r.ano = :ano GROUP BY r.competencia, r.bandeira_tarifaria ORDER BY r.competencia;", "fonte": "Templates SQL Certificados V-Energy / ANEEL"},
]


# ── Funções de Indexação ──────────────────────────────────────────────────────

INSERT_SQL = """
INSERT INTO tb_conhecimento_vetorial (id, categoria, titulo, conteudo, fonte, embedding)
VALUES (%s, %s, %s, %s, %s, %s::vector)
ON CONFLICT (categoria, titulo, md5(conteudo)) DO UPDATE SET
    embedding = EXCLUDED.embedding,
    fonte = EXCLUDED.fonte,
    metadados = EXCLUDED.metadados;
"""


def _gerar_embedding(texto: str, modelo) -> List[float]:
    vetor = modelo.encode(texto, normalize_embeddings=True)
    return vetor.tolist()


def _embedding_para_pg(vetor: List[float]) -> str:
    return f"[{','.join(str(v) for v in vetor)}]"


def indexar_conhecimento(db_url: Optional[str] = None) -> None:
    """
    Popula a base vetorial com o conhecimento inicial da V-Energy.
    Usa INSERT ... ON CONFLICT DO NOTHING, portanto é idempotente.
    """
    db_url = db_url or os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL não definida.")
        sys.exit(1)

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.error("Instale sentence-transformers: pip install sentence-transformers")
        sys.exit(1)

    logger.info("Carregando modelo de embedding...")
    modelo = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    lotes = [
        ("glossario",      GLOSSARIO),
        ("esquema",        ESQUEMA_COLUNAS),
        ("prodist",        REGRAS_SETORIAIS),
        ("templates",      TEMPLATES_SQL),
    ]

    try:
        import psycopg2
    except ImportError:
        logger.error("Instale psycopg2-binary: pip install psycopg2-binary")
        sys.exit(1)

    total_inseridos = 0
    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cur:
            for categoria, itens in lotes:
                for item in itens:
                    texto_para_embed = f"{item['titulo']}. {item['conteudo']}"
                    embedding = _gerar_embedding(texto_para_embed, modelo)
                    cur.execute(INSERT_SQL, (
                        str(uuid.uuid4()),
                        categoria,
                        item["titulo"],
                        item["conteudo"],
                        item.get("fonte", ""),
                        _embedding_para_pg(embedding),
                    ))
                    total_inseridos += 1
                logger.info("Lote '%s': %d itens indexados.", categoria, len(itens))
        conn.commit()

    logger.info("✅  Indexação concluída. Total: %d documentos.", total_inseridos)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    indexar_conhecimento()
