"""
Testes de Qualidade de Dados (Data Quality Gate) - Camada Gold
Verifica o cumprimento do Contrato de Dados da Gold nos 4 eixos:
1. Integridade Referencial (Zero órfãos)
2. Unicidade e Completude de Chaves Primárias
3. Consistência Contábil e Regras de Negócio
4. Coerência Temporal
"""

import sqlite3
import pytest
from scripts.validador_qualidade import validar_banco_sqlite, ResultadoValidacao


@pytest.fixture
def conexao_banco_valido():
    """Cria um banco SQLite em memória com dados mínimos que respeitam 100% o contrato Gold."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE dim_unidade_consumidora (
            id_uc TEXT PRIMARY KEY,
            alimentador TEXT,
            classe TEXT,
            municipio TEXT,
            bairro TEXT
        );
        INSERT INTO dim_unidade_consumidora VALUES
            ('UC001', 'ALIM_A', 'Residencial', 'Recife', 'Boa Viagem'),
            ('UC002', 'ALIM_B', 'Comercial', 'Olinda', 'Bairro Novo');

        CREATE TABLE dim_alimentador (
            alimentador TEXT PRIMARY KEY,
            total_ucs INTEGER
        );
        INSERT INTO dim_alimentador VALUES
            ('ALIM_A', 1),
            ('ALIM_B', 1);

        CREATE TABLE fact_faturamento (
            id_fatura TEXT PRIMARY KEY,
            id_uc TEXT,
            competencia TEXT,
            data_emissao TEXT,
            data_vencimento TEXT,
            data_pagamento TEXT,
            valor_energia REAL,
            tributos REAL,
            receita_faturada REAL,
            bandeira_tarifaria TEXT,
            dias_atraso INTEGER
        );
        INSERT INTO fact_faturamento VALUES
            ('FAT001', 'UC001', '2024-01-01', '2024-01-10', '2024-01-22', '2024-01-20', 100.0, 20.0, 120.0, 'VERDE', 0),
            ('FAT002', 'UC002', '2024-01-01', '2024-01-15', '2024-01-27', NULL, 200.0, 40.0, 240.0, 'AMARELA', 5);

        CREATE TABLE fact_leituras (
            id_leitura TEXT PRIMARY KEY,
            id_uc TEXT,
            competencia TEXT,
            data_leitura TEXT,
            consumo_kwh REAL
        );
        INSERT INTO fact_leituras VALUES
            ('LEIT001', 'UC001', '2024-01-01', '2024-01-10', 150.0),
            ('LEIT002', 'UC002', '2024-01-01', '2024-01-15', 280.0);

        CREATE TABLE fact_ocorrencias (
            id_ocorrencia TEXT PRIMARY KEY,
            id_uc TEXT,
            alimentador TEXT,
            duracao_min REAL,
            data_abertura TEXT,
            data_encerramento TEXT
        );
        INSERT INTO fact_ocorrencias VALUES
            ('OCO001', 'UC001', 'ALIM_A', 45.0, '2024-01-05 10:00:00', '2024-01-05 10:45:00');

        CREATE TABLE agg_continuidade_alimentador (
            alimentador TEXT,
            competencia TEXT,
            dec REAL,
            fec REAL,
            PRIMARY KEY (alimentador, competencia)
        );
        INSERT INTO agg_continuidade_alimentador VALUES
            ('ALIM_A', '2024-01-01', 0.75, 1.0),
            ('ALIM_A', '2024-02-01', 0.50, 1.0),
            ('ALIM_B', '2024-01-01', 0.0, 0.0);
    """)
    conn.commit()
    yield conn
    conn.close()


def test_validacao_sucesso_quando_dados_integros(conexao_banco_valido):
    res = validar_banco_sqlite(conexao_banco_valido)
    assert res.sucesso is True
    assert len(res.erros) == 0
    assert res.total_verificacoes > 0


def test_falha_quando_chave_primaria_duplicada(conexao_banco_valido):
    cur = conexao_banco_valido.cursor()
    # Remove restrição de PK recriando como tabela sem PK estrita para simular CSV com duplicatas
    cur.execute("CREATE TABLE temp_uc AS SELECT * FROM dim_unidade_consumidora;")
    cur.execute("INSERT INTO temp_uc VALUES ('UC001', 'ALIM_A', 'Residencial', 'Recife', 'Boa Viagem');")
    cur.execute("DROP TABLE dim_unidade_consumidora;")
    cur.execute("ALTER TABLE temp_uc RENAME TO dim_unidade_consumidora;")
    conexao_banco_valido.commit()

    res = validar_banco_sqlite(conexao_banco_valido)
    assert res.sucesso is False
    assert any("dim_unidade_consumidora" in e and "duplicad" in e.lower() for e in res.erros)


def test_falha_quando_registro_orfa_faturamento(conexao_banco_valido):
    cur = conexao_banco_valido.cursor()
    cur.execute("""
        INSERT INTO fact_faturamento VALUES
            ('FAT_ORFA', 'UC_INEXISTENTE', '2024-01-01', '2024-01-10', '2024-01-22', NULL, 50.0, 10.0, 60.0, 'VERDE', 0)
    """)
    conexao_banco_valido.commit()

    res = validar_banco_sqlite(conexao_banco_valido)
    assert res.sucesso is False
    assert any("fact_faturamento" in e and "órfã" in e.lower() for e in res.erros)


def test_falha_quando_inconsistencia_contabil(conexao_banco_valido):
    cur = conexao_banco_valido.cursor()
    # receita_faturada (500) != valor_energia (100) + tributos (20)
    cur.execute("UPDATE fact_faturamento SET receita_faturada = 500.0 WHERE id_fatura = 'FAT001'")
    conexao_banco_valido.commit()

    res = validar_banco_sqlite(conexao_banco_valido)
    assert res.sucesso is False
    assert any("contábil" in e.lower() or "receita_faturada" in e.lower() for e in res.erros)


def test_falha_quando_coerencia_temporal_violada(conexao_banco_valido):
    cur = conexao_banco_valido.cursor()
    # Vencimento não é emissão + 12 dias
    cur.execute("UPDATE fact_faturamento SET data_vencimento = '2024-01-30' WHERE id_fatura = 'FAT001'")
    conexao_banco_valido.commit()

    res = validar_banco_sqlite(conexao_banco_valido)
    assert res.sucesso is False
    assert any("vencimento" in e.lower() or "temporal" in e.lower() for e in res.erros)


def test_falha_quando_indicadores_aneel_negativos(conexao_banco_valido):
    cur = conexao_banco_valido.cursor()
    cur.execute("UPDATE agg_continuidade_alimentador SET dec = -1.5 WHERE alimentador = 'ALIM_A'")
    conexao_banco_valido.commit()

    res = validar_banco_sqlite(conexao_banco_valido)
    assert res.sucesso is False
    assert any("dec" in e.lower() or "negativo" in e.lower() for e in res.erros)
