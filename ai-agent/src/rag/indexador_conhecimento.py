"""
Indexador de Conhecimento — popula a base vetorial (tb_conhecimento_vetorial) com:
  1. Glossário de termos coloquiais → técnicos da V-Energy
  2. Esquema e descrição das colunas da camada Gold
  3. Regras setoriais: PRODIST Módulo 8, Bandeiras Tarifárias, Geração Distribuída
  4. Templates SQL analíticos pré-aprovados

Execute uma vez no setup do ambiente:
  python -m ai_agent.src.rag.indexador_conhecimento
"""
from __future__ import annotations

import logging
import os
import sys
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("venergy.indexador_conhecimento")

# ── Conteúdo a ser indexado ───────────────────────────────────────────────────

GLOSSARIO: List[Dict[str, Any]] = [
    {"titulo": "conta de luz", "conteudo": "Corresponde à fatura de energia elétrica emitida mensalmente pela V-Energy. Os dados estão em fact_faturamento (receita_faturada, data_vencimento, status_pagamento).", "fonte": "Glossário V-Energy"},
    {"titulo": "falta de luz / queda de energia", "conteudo": "Evento de interrupção no fornecimento de energia. Registrado em fact_ocorrencias com campos: data_inicio, data_fim, duracao_minutos, causa_interrupcao, alimentador_id.", "fonte": "Glossário V-Energy"},
    {"titulo": "gato / desvio de energia / fraude", "conteudo": "Ligação clandestina ou adulteração de medidor. Identificada em fact_inspecoes. Causa perda não técnica de receita.", "fonte": "Glossário V-Energy"},
    {"titulo": "relógio / medidor", "conteudo": "Equipamento de medição de consumo elétrico (medidor) da UC. Dados de leitura em fact_leituras (leitura_anterior, leitura_atual, consumo_medido_kwh).", "fonte": "Glossário V-Energy"},
    {"titulo": "UC / unidade consumidora", "conteudo": "Unidade consumidora: conjunto de instalações e equipamentos de um cliente conectado à rede. Cadastro em dim_unidade_consumidora (uc_id, municipio, bairro, classe, subgrupo).", "fonte": "Glossário V-Energy"},
    {"titulo": "inadimplência", "conteudo": "UC com fatura(s) em status 'Atrasado' na tabela fact_faturamento. Filtro: WHERE status_pagamento = 'Atrasado'.", "fonte": "Glossário V-Energy"},
    {"titulo": "corte / supressão", "conteudo": "Desligamento do fornecimento por falta de pagamento. Evento registrado em fact_atendimentos com motivo_contato contendo 'Corte' ou 'Supressão'.", "fonte": "Glossário V-Energy"},
    {"titulo": "religação", "conteudo": "Reativação do fornecimento após pagamento em atraso. Registrada em fact_atendimentos (motivo_contato = 'Religação').", "fonte": "Glossário V-Energy"},
    {"titulo": "bandeira / bandeira tarifária", "conteudo": "Sinal de custo adicional na conta de luz. Definido pela ANEEL conforme condições hídricas do sistema. Valores em fact_faturamento (bandeira_tarifaria, valor_bandeira). Verde: sem adicional. Amarela: R$ 0,01874/kWh. Vermelha 1: R$ 0,03971/kWh. Vermelha 2: R$ 0,09492/kWh.", "fonte": "ANEEL / Glossário V-Energy"},
    {"titulo": "GD / geração distribuída / solar", "conteudo": "Microgeração ou minigeração de energia elétrica pelo próprio consumidor (ex.: painéis solares). UC marcada com tem_geracao_distribuida = TRUE em dim_unidade_consumidora. Créditos compensados em fact_faturamento.", "fonte": "Lei 14.300/2022 / Glossário V-Energy"},
    {"titulo": "alimentador / circuito", "conteudo": "Trecho de rede de média tensão que distribui energia a um grupo de UCs. Dados em dim_alimentadores (alimentador_id, subestacao, municipio, total_ucs_atendidas).", "fonte": "Glossário V-Energy"},
    {"titulo": "subgrupo tarifário", "conteudo": "Classificação da UC para fins de tarifação: B1=Residencial baixa renda/padrão, B2=Rural, B3=Comercial/industrial BT, A4=Industrial MT. Campo subgrupo em dim_unidade_consumidora.", "fonte": "ANEEL Resolução 414 / Glossário V-Energy"},
]

ESQUEMA_COLUNAS: List[Dict[str, Any]] = [
    {"titulo": "dim_unidade_consumidora", "conteudo": "Cadastro central das UCs. Colunas: uc_id (PK), municipio (14 municípios da concessão), bairro, classe (Residencial/Comercial/Industrial/Rural), subgrupo (B1/B2/B3/A4), alimentador_id (FK), status_ligacao (Ligada/Cortada/Suspensa), tem_geracao_distribuida (BOOLEAN).", "fonte": "Dicionário de Dados Gold"},
    {"titulo": "fact_faturamento", "conteudo": "Faturas mensais emitidas por UC. Colunas: fatura_id, uc_id (FK), competencia (YYYY-MM), ano, mes, volume_faturado_kwh, receita_faturada (R$), valor_tarifa (R$/kWh), bandeira_tarifaria, valor_bandeira, status_pagamento (Pago/Pendente/Atrasado), data_vencimento, data_pagamento.", "fonte": "Dicionário de Dados Gold"},
    {"titulo": "fact_leituras", "conteudo": "Leituras mensais dos medidores. Colunas: leitura_id, uc_id (FK), competencia, leitura_anterior (kWh), leitura_atual (kWh), consumo_medido_kwh (diferença entre leituras), tipo_leitura (Real/Estimada).", "fonte": "Dicionário de Dados Gold"},
    {"titulo": "fact_ocorrencias", "conteudo": "Interrupções de fornecimento. Colunas: ocorrencia_id, alimentador_id (FK), uc_id (FK, nullable), data_inicio, data_fim, duracao_minutos, causa_interrupcao (Programada/Emergencial/Falta de Pagamento/Clima).", "fonte": "Dicionário de Dados Gold"},
    {"titulo": "fact_atendimentos", "conteudo": "Chamados do call center e campo. Colunas: chamado_id, uc_id (FK), data_abertura, motivo_contato (Corte/Religação/Reclamação/Informação), status (Aberto/Concluído), nota_satisfacao (1-5).", "fonte": "Dicionário de Dados Gold"},
    {"titulo": "dim_alimentadores", "conteudo": "Circuitos de distribuição. Colunas: alimentador_id (PK), subestacao, municipio, total_ucs_atendidas.", "fonte": "Dicionário de Dados Gold"},
]

REGRAS_SETORIAIS: List[Dict[str, Any]] = [
    {"titulo": "Indicador DEC (Duração Equivalente de Continuidade)", "conteudo": "DEC = Somatório(duração de cada interrupção × UCs afetadas) / Total de UCs do conjunto. Mede quantas horas em média cada UC ficou sem energia no período. Regulado pelo PRODIST Módulo 8 da ANEEL. Limites anuais definidos por conjunto e faixa de tensão. Fonte de dados: fact_ocorrencias e dim_alimentadores.", "fonte": "PRODIST Módulo 8 / ANEEL"},
    {"titulo": "Indicador FEC (Frequência Equivalente de Continuidade)", "conteudo": "FEC = Somatório(número de interrupções × UCs afetadas) / Total de UCs do conjunto. Mede quantas vezes em média cada UC foi interrompida no período. Complementar ao DEC. Regulado pelo PRODIST Módulo 8. Fonte: fact_ocorrencias agrupado por alimentador_id.", "fonte": "PRODIST Módulo 8 / ANEEL"},
    {"titulo": "Bandeiras Tarifárias ANEEL (adicional por kWh)", "conteudo": "Sistema de sinalização tarifária conforme condições do reservatório hídrico nacional: Verde = R$ 0,00/kWh; Amarela = R$ 0,01874/kWh; Vermelha Patamar 1 = R$ 0,03971/kWh; Vermelha Patamar 2 = R$ 0,09492/kWh. Valores vigentes da resolução ANEEL. Coluna bandeira_tarifaria em fact_faturamento.", "fonte": "ANEEL Resolução Homologatória"},
    {"titulo": "Geração Distribuída e compensação de créditos (Lei 14.300/2022)", "conteudo": "UCs com microgeração solar (tem_geracao_distribuida=TRUE) geram créditos de energia que compensam o consumo da rede. O crédito reduz o volume faturado líquido. Modalidades: autoprodução, condomínio, empreendimento de múltiplas UCs. A compensação é aplicada mensalmente no faturamento.", "fonte": "Lei 14.300/2022 / ANEEL"},
    {"titulo": "Perdas técnicas e não técnicas de energia", "conteudo": "Perdas técnicas: dissipação de energia na rede por efeito Joule (inevitável). Perdas não técnicas (comerciais): desvios de energia, fraudes, erros de medição. O diagnóstico de perdas compara energia injetada no alimentador versus energia faturada às UCs. Dados em fact_leituras e fact_faturamento.", "fonte": "PRODIST Módulo 1 / V-Energy"},
    {"titulo": "Decomposição de Receita: Preço versus Volume", "conteudo": "A variação de receita entre dois períodos pode ser decomposta em: (1) Efeito Preço = variação na tarifa × volume base; (2) Efeito Volume = variação no consumo × tarifa base; (3) Efeito Mix = mudança na composição de classes. Metodologia padrão de diagnóstico de receita da distribuidora.", "fonte": "Diagnóstico V-Energy / Metodologia Interna"},
    {"titulo": "Classes de consumo e suas características", "conteudo": "Residencial (B1): maior volume de UCs, menor consumo médio (~200-350 kWh/mês), maior sensibilidade à bandeira tarifária. Comercial (B3): consumo médio a alto, impacto significativo em receita. Industrial (A4): alta tensão, tarifa diferenciada, menor número de UCs mas alta receita unitária. Rural (B2): sazonalidade de consumo agrícola.", "fonte": "ANEEL Resolução 414 / V-Energy"},
]

TEMPLATES_SQL: List[Dict[str, Any]] = [
    {"titulo": "Receita total por município e ano", "conteudo": "SELECT u.municipio, f.ano, SUM(f.receita_faturada) AS receita_total FROM fact_faturamento f JOIN dim_unidade_consumidora u ON f.uc_id = u.uc_id GROUP BY u.municipio, f.ano ORDER BY f.ano DESC, receita_total DESC;", "fonte": "Templates SQL Certificados V-Energy"},
    {"titulo": "UCs inadimplentes por município e classe", "conteudo": "SELECT u.municipio, u.classe, COUNT(*) AS total_inadimplentes FROM fact_faturamento f JOIN dim_unidade_consumidora u ON f.uc_id = u.uc_id WHERE f.status_pagamento = 'Atrasado' GROUP BY u.municipio, u.classe ORDER BY total_inadimplentes DESC;", "fonte": "Templates SQL Certificados V-Energy"},
    {"titulo": "Cálculo simplificado de DEC por alimentador", "conteudo": "SELECT o.alimentador_id, a.municipio, SUM(o.duracao_minutos * a.total_ucs_atendidas) / NULLIF(a.total_ucs_atendidas, 0) / 60.0 AS dec_horas FROM fact_ocorrencias o JOIN dim_alimentadores a ON o.alimentador_id = a.alimentador_id WHERE EXTRACT(YEAR FROM o.data_inicio) = :ano GROUP BY o.alimentador_id, a.municipio, a.total_ucs_atendidas ORDER BY dec_horas DESC;", "fonte": "Templates SQL Certificados V-Energy / PRODIST Módulo 8"},
    {"titulo": "Impacto da bandeira tarifária na receita mensal", "conteudo": "SELECT f.competencia, f.bandeira_tarifaria, SUM(f.valor_bandeira) AS receita_adicional_bandeira, SUM(f.receita_faturada) AS receita_total FROM fact_faturamento f WHERE f.ano = :ano GROUP BY f.competencia, f.bandeira_tarifaria ORDER BY f.competencia;", "fonte": "Templates SQL Certificados V-Energy / ANEEL"},
]


# ── Funções de Indexação ──────────────────────────────────────────────────────

INSERT_SQL = """
INSERT INTO tb_conhecimento_vetorial (id, categoria, titulo, conteudo, fonte, embedding)
VALUES (%s, %s, %s, %s, %s, %s::vector)
ON CONFLICT DO NOTHING;
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
