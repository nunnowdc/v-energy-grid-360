"""
scripts/validador_qualidade.py
V-Energy Grid 360 · Motor de Validação Automatizada de Qualidade de Dados (Data Quality Gate)

Implementa as regras canônicas do Contrato de Dados da Gold nos 4 eixos:
1. Integridade Referencial (Zero órfãos)
2. Unicidade e Completude de Chaves Primárias
3. Consistência Contábil e Regras de Negócio
4. Coerência Temporal
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import sqlite3


@dataclass
class ResultadoValidacao:
    sucesso: bool = True
    erros: List[str] = field(default_factory=list)
    avisos: List[str] = field(default_factory=list)
    total_verificacoes: int = 0

    def registrar_erro(self, mensagem: str):
        self.sucesso = False
        self.erros.append(mensagem)

    def registrar_aviso(self, mensagem: str):
        self.avisos.append(mensagem)


def _tabela_existe_sqlite(cursor, nome_tabela: str) -> bool:
    cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (nome_tabela,))
    return cursor.fetchone() is not None


def _tabela_existe_pg(cursor, nome_tabela: str) -> bool:
    cursor.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = %s
    """, (nome_tabela,))
    return cursor.fetchone() is not None


def validar_banco_sqlite(conn: sqlite3.Connection) -> ResultadoValidacao:
    """Executa a suíte completa de validação de qualidade no banco SQLite."""
    res = ResultadoValidacao()
    cur = conn.cursor()

    # Tabelas e suas chaves primárias
    pks = {
        "dim_unidade_consumidora": ("id_uc",),
        "dim_alimentador": ("alimentador",),
        "dim_medidor": ("id_medidor",),
        "dim_geracao_distribuida": ("id_uc",),
        "dim_competencia": ("competencia",),
        "fact_faturamento": ("id_fatura",),
        "fact_leituras": ("id_leitura",),
        "fact_ocorrencias": ("id_ocorrencia",),
        "fact_atendimentos": ("protocolo",),
        "fact_inspecoes": ("id_inspecao",),
        "fila_inspecao": ("prioridade",),
        "agg_continuidade_alimentador": ("alimentador", "competencia"),
        "agg_continuidade_alimentador_anual": ("alimentador", "ano"),
    }

    # Eixo 2: Unicidade e Não-Nulos de Chaves Primárias / Grão Analítico
    for tabela, colunas in pks.items():
        if not _tabela_existe_sqlite(cur, tabela):
            continue

        res.total_verificacoes += 1
        cols_sql = ", ".join(colunas)
        pk_desc = "(" + cols_sql + ")" if len(colunas) > 1 else colunas[0]

        # Nulos em qualquer coluna da chave
        cond_nulos = " OR ".join([f"({c} IS NULL OR trim(CAST({c} AS TEXT)) = '')" for c in colunas])
        cur.execute(f"SELECT COUNT(*) FROM {tabela} WHERE {cond_nulos}")
        qtd_nulos = cur.fetchone()[0]
        if qtd_nulos > 0:
            res.registrar_erro(f"Tabela {tabela}: {qtd_nulos} chaves nulas na chave {pk_desc}.")

        # Duplicatas na chave (simples ou composta)
        cur.execute(f"""
            SELECT COUNT(*) FROM (
                SELECT {cols_sql} FROM {tabela} GROUP BY {cols_sql} HAVING COUNT(*) > 1
            )
        """)
        qtd_dup = cur.fetchone()[0]
        if qtd_dup > 0:
            res.registrar_erro(f"Tabela {tabela}: Chave {pk_desc} possui {qtd_dup} valores duplicados.")

    # Eixo 1: Integridade Referencial (Zero órfãos)
    relacionamentos_uc = [
        ("fact_faturamento", "id_uc"),
        ("fact_leituras", "id_uc"),
        ("fact_ocorrencias", "id_uc"),
        ("fact_atendimentos", "id_uc"),
        ("fact_inspecoes", "id_uc"),
        ("fila_inspecao", "id_uc"),
        ("dim_geracao_distribuida", "id_uc"),
    ]

    if _tabela_existe_sqlite(cur, "dim_unidade_consumidora"):
        for tab_filha, fk in relacionamentos_uc:
            if not _tabela_existe_sqlite(cur, tab_filha):
                continue
            res.total_verificacoes += 1
            cur.execute(f"""
                SELECT COUNT(*) FROM {tab_filha} f
                LEFT JOIN dim_unidade_consumidora d ON f.{fk} = d.id_uc
                WHERE f.{fk} IS NOT NULL AND d.id_uc IS NULL
            """)
            orfaos = cur.fetchone()[0]
            if orfaos > 0:
                res.registrar_erro(f"Integridade Referencial: Tabela {tab_filha} possui {orfaos} registros com chave órfã para dim_unidade_consumidora.")

    if _tabela_existe_sqlite(cur, "dim_alimentador") and _tabela_existe_sqlite(cur, "fact_ocorrencias"):
        res.total_verificacoes += 1
        cur.execute("""
            SELECT COUNT(*) FROM fact_ocorrencias f
            LEFT JOIN dim_alimentador d ON f.alimentador = d.alimentador
            WHERE f.alimentador IS NOT NULL AND d.alimentador IS NULL
        """)
        orfaos_alim = cur.fetchone()[0]
        if orfaos_alim > 0:
            res.registrar_erro(f"Integridade Referencial: fact_ocorrencias possui {orfaos_alim} alimentadores órfãos.")

    # Eixo 3: Consistência Contábil e Regras de Negócio
    if _tabela_existe_sqlite(cur, "fact_faturamento"):
        res.total_verificacoes += 1
        cur.execute("""
            SELECT COUNT(*) FROM fact_faturamento
            WHERE abs(receita_faturada - (valor_energia + tributos)) > 0.05
        """)
        erros_contabeis = cur.fetchone()[0]
        if erros_contabeis > 0:
            res.registrar_erro(f"Consistência Contábil: fact_faturamento possui {erros_contabeis} registros onde receita_faturada != valor_energia + tributos.")

        res.total_verificacoes += 1
        cur.execute("SELECT COUNT(*) FROM fact_faturamento WHERE dias_atraso < 0")
        dias_neg = cur.fetchone()[0]
        if dias_neg > 0:
            res.registrar_erro(f"Regra de Domínio: fact_faturamento possui {dias_neg} faturas com dias_atraso negativo.")

        res.total_verificacoes += 1
        cur.execute("""
            SELECT COUNT(*) FROM fact_faturamento
            WHERE bandeira_tarifaria NOT IN ('VERDE', 'AMARELA', 'VERMELHA_P1', 'VERMELHA_P2')
        """)
        band_inval = cur.fetchone()[0]
        if band_inval > 0:
            res.registrar_erro(f"Regra de Domínio: fact_faturamento possui {band_inval} registros com bandeira tarifária fora do domínio regulatório.")

    if _tabela_existe_sqlite(cur, "fact_leituras"):
        res.total_verificacoes += 1
        cur.execute("SELECT COUNT(*) FROM fact_leituras WHERE consumo_kwh < 0")
        consumo_neg = cur.fetchone()[0]
        if consumo_neg > 0:
            res.registrar_erro(f"Regra de Domínio: fact_leituras possui {consumo_neg} leituras com consumo_kwh negativo.")

    if _tabela_existe_sqlite(cur, "agg_continuidade_alimentador"):
        res.total_verificacoes += 1
        cur.execute("SELECT COUNT(*) FROM agg_continuidade_alimentador WHERE dec < 0 OR fec < 0")
        indicadores_neg = cur.fetchone()[0]
        if indicadores_neg > 0:
            res.registrar_erro(f"Regra de Domínio: agg_continuidade_alimentador possui {indicadores_neg} registros com indicador DEC ou FEC negativo.")

    if _tabela_existe_sqlite(cur, "fila_inspecao"):
        res.total_verificacoes += 1
        cur.execute("SELECT COUNT(*) FROM fila_inspecao WHERE score < 0 OR score > 100")
        score_inval = cur.fetchone()[0]
        if score_inval > 0:
            res.registrar_erro(f"Regra de Domínio: fila_inspecao possui {score_inval} UCs com score de suspeita fora do intervalo [0, 100].")

    # Eixo 4: Coerência Temporal
    if _tabela_existe_sqlite(cur, "fact_faturamento"):
        res.total_verificacoes += 1
        # Vencimento deve ser exatamente emissão + 12 dias
        cur.execute("""
            SELECT COUNT(*) FROM fact_faturamento
            WHERE data_emissao IS NOT NULL
              AND data_vencimento IS NOT NULL
              AND date(data_vencimento) != date(data_emissao, '+12 day')
        """)
        venc_inval = cur.fetchone()[0]
        if venc_inval > 0:
            res.registrar_erro(f"Coerência Temporal: fact_faturamento possui {venc_inval} registros onde data_vencimento != data_emissao + 12 dias.")

    if _tabela_existe_sqlite(cur, "fact_ocorrencias"):
        res.total_verificacoes += 1
        cur.execute("""
            SELECT COUNT(*) FROM fact_ocorrencias
            WHERE data_encerramento IS NOT NULL
              AND data_abertura IS NOT NULL
              AND data_encerramento < data_abertura
        """)
        duracao_neg = cur.fetchone()[0]
        if duracao_neg > 0:
            res.registrar_erro(f"Coerência Temporal: fact_ocorrencias possui {duracao_neg} ocorrências com data de encerramento anterior à data de abertura.")

    return res


def validar_banco_postgres(cursor) -> ResultadoValidacao:
    """Executa a suíte completa de validação de qualidade no banco PostgreSQL."""
    res = ResultadoValidacao()

    pks = {
        "dim_unidade_consumidora": ("id_uc",),
        "dim_alimentador": ("alimentador",),
        "dim_medidor": ("id_medidor",),
        "dim_geracao_distribuida": ("id_uc",),
        "dim_competencia": ("competencia",),
        "fact_faturamento": ("id_fatura",),
        "fact_leituras": ("id_leitura",),
        "fact_ocorrencias": ("id_ocorrencia",),
        "fact_atendimentos": ("protocolo",),
        "fact_inspecoes": ("id_inspecao",),
        "fila_inspecao": ("prioridade",),
        "agg_continuidade_alimentador": ("alimentador", "competencia"),
        "agg_continuidade_alimentador_anual": ("alimentador", "ano"),
    }

    # Eixo 2: Unicidade e Não-Nulos de Chaves Primárias / Grão Analítico
    for tabela, colunas in pks.items():
        if not _tabela_existe_pg(cursor, tabela):
            continue
        res.total_verificacoes += 1
        cols_sql = ", ".join(colunas)
        pk_desc = "(" + cols_sql + ")" if len(colunas) > 1 else colunas[0]

        cond_nulos = " OR ".join([f"{c} IS NULL" for c in colunas])
        cursor.execute(f"SELECT COUNT(*) FROM {tabela} WHERE {cond_nulos};")
        qtd_nulos = cursor.fetchone()[0]
        if qtd_nulos > 0:
            res.registrar_erro(f"Tabela {tabela}: {qtd_nulos} chaves nulas na chave {pk_desc}.")

        cursor.execute(f"""
            SELECT COUNT(*) FROM (
                SELECT {cols_sql} FROM {tabela} GROUP BY {cols_sql} HAVING COUNT(*) > 1
            ) t;
        """)
        qtd_dup = cursor.fetchone()[0]
        if qtd_dup > 0:
            res.registrar_erro(f"Tabela {tabela}: Chave {pk_desc} possui {qtd_dup} valores duplicados.")

    # Eixo 1: Integridade Referencial
    relacionamentos_uc = [
        ("fact_faturamento", "id_uc"),
        ("fact_leituras", "id_uc"),
        ("fact_ocorrencias", "id_uc"),
        ("fact_atendimentos", "id_uc"),
        ("fact_inspecoes", "id_uc"),
        ("fila_inspecao", "id_uc"),
        ("dim_geracao_distribuida", "id_uc"),
    ]

    if _tabela_existe_pg(cursor, "dim_unidade_consumidora"):
        for tab_filha, fk in relacionamentos_uc:
            if not _tabela_existe_pg(cursor, tab_filha):
                continue
            res.total_verificacoes += 1
            cursor.execute(f"""
                SELECT COUNT(*) FROM {tab_filha} f
                LEFT JOIN dim_unidade_consumidora d ON f.{fk} = d.id_uc
                WHERE f.{fk} IS NOT NULL AND d.id_uc IS NULL;
            """)
            orfaos = cursor.fetchone()[0]
            if orfaos > 0:
                res.registrar_erro(f"Integridade Referencial: Tabela {tab_filha} possui {orfaos} registros com chave órfã para dim_unidade_consumidora.")

    if _tabela_existe_pg(cursor, "dim_alimentador") and _tabela_existe_pg(cursor, "fact_ocorrencias"):
        res.total_verificacoes += 1
        cursor.execute("""
            SELECT COUNT(*) FROM fact_ocorrencias f
            LEFT JOIN dim_alimentador d ON f.alimentador = d.alimentador
            WHERE f.alimentador IS NOT NULL AND d.alimentador IS NULL;
        """)
        orfaos_alim = cursor.fetchone()[0]
        if orfaos_alim > 0:
            res.registrar_erro(f"Integridade Referencial: fact_ocorrencias possui {orfaos_alim} alimentadores órfãos.")

    # Eixo 3: Consistência Contábil e Regras de Negócio
    if _tabela_existe_pg(cursor, "fact_faturamento"):
        res.total_verificacoes += 1
        cursor.execute("""
            SELECT COUNT(*) FROM fact_faturamento
            WHERE abs(receita_faturada - (valor_energia + tributos)) > 0.05;
        """)
        erros_contabeis = cursor.fetchone()[0]
        if erros_contabeis > 0:
            res.registrar_erro(f"Consistência Contábil: fact_faturamento possui {erros_contabeis} registros onde receita_faturada != valor_energia + tributos.")

        res.total_verificacoes += 1
        cursor.execute("SELECT COUNT(*) FROM fact_faturamento WHERE dias_atraso < 0;")
        dias_neg = cursor.fetchone()[0]
        if dias_neg > 0:
            res.registrar_erro(f"Regra de Domínio: fact_faturamento possui {dias_neg} faturas com dias_atraso negativo.")

        res.total_verificacoes += 1
        cursor.execute("""
            SELECT COUNT(*) FROM fact_faturamento
            WHERE bandeira_tarifaria NOT IN ('VERDE', 'AMARELA', 'VERMELHA_P1', 'VERMELHA_P2');
        """)
        band_inval = cursor.fetchone()[0]
        if band_inval > 0:
            res.registrar_erro(f"Regra de Domínio: fact_faturamento possui {band_inval} registros com bandeira tarifária fora do domínio regulatório.")

    if _tabela_existe_pg(cursor, "fact_leituras"):
        res.total_verificacoes += 1
        cursor.execute("SELECT COUNT(*) FROM fact_leituras WHERE consumo_kwh < 0;")
        consumo_neg = cursor.fetchone()[0]
        if consumo_neg > 0:
            res.registrar_erro(f"Regra de Domínio: fact_leituras possui {consumo_neg} leituras com consumo_kwh negativo.")

    if _tabela_existe_pg(cursor, "agg_continuidade_alimentador"):
        res.total_verificacoes += 1
        cursor.execute("SELECT COUNT(*) FROM agg_continuidade_alimentador WHERE dec < 0 OR fec < 0;")
        indicadores_neg = cursor.fetchone()[0]
        if indicadores_neg > 0:
            res.registrar_erro(f"Regra de Domínio: agg_continuidade_alimentador possui {indicadores_neg} registros com indicador DEC ou FEC negativo.")

    if _tabela_existe_pg(cursor, "fila_inspecao"):
        res.total_verificacoes += 1
        cursor.execute("SELECT COUNT(*) FROM fila_inspecao WHERE score < 0 OR score > 100;")
        score_inval = cursor.fetchone()[0]
        if score_inval > 0:
            res.registrar_erro(f"Regra de Domínio: fila_inspecao possui {score_inval} UCs com score de suspeita fora do intervalo [0, 100].")

    # Eixo 4: Coerência Temporal
    if _tabela_existe_pg(cursor, "fact_faturamento"):
        res.total_verificacoes += 1
        cursor.execute("""
            SELECT COUNT(*) FROM fact_faturamento
            WHERE data_emissao IS NOT NULL
              AND data_vencimento IS NOT NULL
              AND data_vencimento != data_emissao + INTERVAL '12 days';
        """)
        venc_inval = cursor.fetchone()[0]
        if venc_inval > 0:
            res.registrar_erro(f"Coerência Temporal: fact_faturamento possui {venc_inval} registros onde data_vencimento != data_emissao + 12 dias.")

    if _tabela_existe_pg(cursor, "fact_ocorrencias"):
        res.total_verificacoes += 1
        cursor.execute("""
            SELECT COUNT(*) FROM fact_ocorrencias
            WHERE data_encerramento IS NOT NULL
              AND data_abertura IS NOT NULL
              AND data_encerramento < data_abertura;
        """)
        duracao_neg = cursor.fetchone()[0]
        if duracao_neg > 0:
            res.registrar_erro(f"Coerência Temporal: fact_ocorrencias possui {duracao_neg} ocorrências com data de encerramento anterior à data de abertura.")

    return res
