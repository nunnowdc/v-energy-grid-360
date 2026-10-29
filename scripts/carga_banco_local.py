#!/usr/bin/env python3
"""
scripts/carga_banco_local.py
V-Energy Grid 360 · Ingestão e Seed Local das Tabelas da Camada Gold

Este script automatiza o processo de:
1. Localização e extração do arquivo .zip da release com os CSVs da camada Gold;
2. Criação automática dos esquemas DDL (tabelas e tipos);
3. Carga em massa ultra-rápida no PostgreSQL (via COPY nativo) ou SQLite (fallback/opcional).

Uso:
    python scripts/carga_banco_local.py                 # Carga no PostgreSQL local (padrão)
    python scripts/carga_banco_local.py --sqlite        # Carga em banco local SQLite (data/v_energy_gold.db)
    python scripts/carga_banco_local.py --help          # Exibe opções de conexão
"""

import os
import sys
import glob
import time
import zipfile
import argparse
import subprocess

from dotenv import load_dotenv

load_dotenv()
# Configuração de diretórios
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.validador_qualidade import validar_banco_sqlite, validar_banco_postgres
DATA_DIR = os.path.join(ROOT_DIR, "data")
SQLITE_DB_PATH = os.path.join(DATA_DIR, "v_energy_gold.db")

# DDL PostgreSQL para as tabelas analíticas da camada Gold
DDL_POSTGRES = {
    "dim_unidade_consumidora": """
        CREATE TABLE IF NOT EXISTS dim_unidade_consumidora (
            id_uc VARCHAR(30) PRIMARY KEY,
            nome_titular VARCHAR(255),
            cpf_cnpj_mascarado VARCHAR(50),
            tipo_pessoa VARCHAR(10),
            logradouro VARCHAR(255),
            numero VARCHAR(50),
            bairro VARCHAR(100),
            municipio VARCHAR(100),
            uf VARCHAR(10),
            cep VARCHAR(20),
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            classe VARCHAR(50),
            subgrupo_tarifario VARCHAR(20),
            alimentador VARCHAR(50),
            data_ligacao DATE,
            status VARCHAR(50),
            possui_gd BOOLEAN,
            data_conexao_gd DATE,
            potencia_gd_kwp DOUBLE PRECISION,
            modalidade_gd VARCHAR(100),
            id_medidor_atual VARCHAR(50),
            tipo_medidor_atual VARCHAR(50),
            modelo_medidor_atual VARCHAR(50),
            data_instalacao_medidor_atual DATE,
            trocou_medidor BOOLEAN,
            data_ultima_troca_medidor DATE,
            tipo_medidor_anterior VARCHAR(50),
            cadastro_conflitante BOOLEAN,
            _processado_em TIMESTAMP
        );
    """,
    "dim_alimentador": """
        CREATE TABLE IF NOT EXISTS dim_alimentador (
            alimentador VARCHAR(50) PRIMARY KEY,
            total_ucs BIGINT,
            qtd_municipios BIGINT,
            qtd_bairros BIGINT,
            ucs_residencial BIGINT,
            ucs_comercial BIGINT,
            ucs_industrial BIGINT,
            ucs_rural BIGINT,
            ucs_poder_publico BIGINT,
            municipio_principal VARCHAR(100),
            regiao VARCHAR(50),
            alimentador_pequeno BOOLEAN,
            _processado_em TIMESTAMP
        );
    """,
    "dim_medidor": """
        CREATE TABLE IF NOT EXISTS dim_medidor (
            id_medidor VARCHAR(50) PRIMARY KEY,
            id_uc VARCHAR(30),
            modelo VARCHAR(50),
            tipo VARCHAR(50),
            data_instalacao DATE,
            data_retirada DATE,
            status VARCHAR(50),
            medidor_atual BOOLEAN,
            data_ultima_manutencao DATE,
            _processado_em TIMESTAMP
        );
    """,
    "dim_geracao_distribuida": """
        CREATE TABLE IF NOT EXISTS dim_geracao_distribuida (
            id_uc VARCHAR(30) PRIMARY KEY,
            potencia_kwp DOUBLE PRECISION,
            potencia_corrigida_unidade BOOLEAN,
            data_conexao DATE,
            modalidade VARCHAR(100),
            energia_injetada_kwh_media_mensal DOUBLE PRECISION,
            energia_estimada BOOLEAN,
            energia_reestimada_kwh DOUBLE PRECISION,
            kwh_por_kwp_mes DOUBLE PRECISION,
            _processado_em TIMESTAMP
        );
    """,
    "dim_competencia": """
        CREATE TABLE IF NOT EXISTS dim_competencia (
            competencia DATE PRIMARY KEY,
            mes_referencia VARCHAR(20),
            ano INT,
            mes INT,
            trimestre INT,
            bandeira_tarifaria VARCHAR(50),
            periodo_diagnostico VARCHAR(50),
            _processado_em TIMESTAMP
        );
    """,
    "fact_faturamento": """
        CREATE TABLE IF NOT EXISTS fact_faturamento (
            id_fatura VARCHAR(50) PRIMARY KEY,
            id_uc VARCHAR(30),
            competencia DATE,
            mes_referencia VARCHAR(20),
            ano INT,
            mes INT,
            data_emissao DATE,
            data_vencimento DATE,
            data_pagamento DATE,
            valor_energia DOUBLE PRECISION,
            tributos DOUBLE PRECISION,
            receita_faturada DOUBLE PRECISION,
            receita_recebida DOUBLE PRECISION,
            bandeira_tarifaria VARCHAR(50),
            status VARCHAR(50),
            status_pagamento VARCHAR(50),
            dias_atraso INT,
            consumo_kwh DOUBLE PRECISION,
            preco_medio_kwh DOUBLE PRECISION,
            _processado_em TIMESTAMP
        );
    """,
    "fact_leituras": """
        CREATE TABLE IF NOT EXISTS fact_leituras (
            id_leitura VARCHAR(50) PRIMARY KEY,
            id_uc VARCHAR(30),
            id_medidor VARCHAR(50),
            competencia DATE,
            mes_referencia VARCHAR(20),
            ano INT,
            mes INT,
            data_leitura DATE,
            leitura_anterior DOUBLE PRECISION,
            leitura_atual DOUBLE PRECISION,
            consumo_kwh DOUBLE PRECISION,
            consumo_kwh_declarado DOUBLE PRECISION,
            consumo_imputado BOOLEAN,
            tipo_leitura VARCHAR(50),
            status_qualidade_leitura VARCHAR(50),
            consumo_ano_anterior_kwh DOUBLE PRECISION,
            variacao_ano_anterior_pct DOUBLE PRECISION,
            _processado_em TIMESTAMP
        );
    """,
    "fact_ocorrencias": """
        CREATE TABLE IF NOT EXISTS fact_ocorrencias (
            id_ocorrencia VARCHAR(50) PRIMARY KEY,
            id_uc VARCHAR(30),
            alimentador VARCHAR(50),
            tipo VARCHAR(50),
            causa VARCHAR(100),
            data_abertura TIMESTAMP,
            data_encerramento TIMESTAMP,
            competencia DATE,
            duracao_min DOUBLE PRECISION,
            duracao_h DOUBLE PRECISION,
            dia_critico BOOLEAN,
            duracao_truncada BOOLEAN,
            eh_oscilacao BOOLEAN,
            _processado_em TIMESTAMP
        );
    """,
    "fact_atendimentos": """
        CREATE TABLE IF NOT EXISTS fact_atendimentos (
            protocolo VARCHAR(50) PRIMARY KEY,
            id_uc VARCHAR(30),
            assunto VARCHAR(100),
            subassunto VARCHAR(100),
            canal VARCHAR(50),
            data_abertura TIMESTAMP,
            data_fechamento TIMESTAMP,
            competencia DATE,
            status_chamado VARCHAR(50),
            tempo_resolucao_h DOUBLE PRECISION,
            nota_satisfacao DOUBLE PRECISION,
            qtd_tratativas INT,
            _processado_em TIMESTAMP
        );
    """,
    "fact_inspecoes": """
        CREATE TABLE IF NOT EXISTS fact_inspecoes (
            id_inspecao VARCHAR(50) PRIMARY KEY,
            id_uc VARCHAR(30),
            data DATE,
            data_inspecao DATE,
            mes_inspecao VARCHAR(20),
            inspetor VARCHAR(100),
            resultado VARCHAR(100),
            tipo_irregularidade VARCHAR(100),
            kwh_recuperado DOUBLE PRECISION,
            registro_coerente BOOLEAN,
            aba_origem VARCHAR(50),
            _processado_em TIMESTAMP
        );
    """,
    "fila_inspecao": """
        CREATE TABLE IF NOT EXISTS fila_inspecao (
            prioridade INT PRIMARY KEY,
            id_uc VARCHAR(30),
            score INT,
            motivo_suspeita TEXT,
            kwh_recuperavel_estimado_ano DOUBLE PRECISION,
            nome_titular VARCHAR(255),
            logradouro VARCHAR(255),
            numero VARCHAR(50),
            bairro VARCHAR(100),
            municipio VARCHAR(100),
            classe VARCHAR(50),
            alimentador VARCHAR(50),
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            tipo_medidor_atual VARCHAR(50),
            trocou_medidor BOOLEAN,
            possui_gd BOOLEAN,
            queda_explicada_por_gd BOOLEAN,
            consumo_medio_ano_anterior_kwh DOUBLE PRECISION,
            consumo_medio_recente_kwh DOUBLE PRECISION,
            variacao_consumo_pct DOUBLE PRECISION,
            pct_leituras_estimadas_12m DOUBLE PRECISION,
            anomalias_leitura_12m BIGINT,
            taxa_irregularidade_bairro DOUBLE PRECISION,
            data_ultima_inspecao DATE,
            resultado_ultima_inspecao VARCHAR(100),
            ja_teve_irregularidade BOOLEAN,
            data_referencia DATE,
            _processado_em TIMESTAMP
        );
    """,
    "agg_receita_mensal": """
        CREATE TABLE IF NOT EXISTS agg_receita_mensal (
            competencia DATE,
            mes_referencia VARCHAR(20),
            bandeira_tarifaria VARCHAR(50),
            municipio VARCHAR(100),
            bairro VARCHAR(100),
            classe VARCHAR(50),
            possui_gd BOOLEAN,
            receita_faturada DOUBLE PRECISION,
            receita_recebida DOUBLE PRECISION,
            receita_energia DOUBLE PRECISION,
            consumo_kwh DOUBLE PRECISION,
            ucs_faturadas BIGINT,
            faturas BIGINT,
            faturas_atrasadas BIGINT,
            preco_medio_kwh DOUBLE PRECISION,
            ano INT,
            mes INT,
            _processado_em TIMESTAMP
        );
    """,
    "agg_receita_preco_volume": """
        CREATE TABLE IF NOT EXISTS agg_receita_preco_volume (
            municipio VARCHAR(100),
            bairro VARCHAR(100),
            classe VARCHAR(50),
            possui_gd BOOLEAN,
            receita_p0 DOUBLE PRECISION,
            receita_p1 DOUBLE PRECISION,
            kwh_p0 DOUBLE PRECISION,
            kwh_p1 DOUBLE PRECISION,
            ucs_p0 BIGINT,
            ucs_p1 BIGINT,
            preco_p0 DOUBLE PRECISION,
            preco_p1 DOUBLE PRECISION,
            variacao_receita DOUBLE PRECISION,
            efeito_volume DOUBLE PRECISION,
            efeito_preco DOUBLE PRECISION,
            variacao_receita_pct DOUBLE PRECISION,
            variacao_volume_pct DOUBLE PRECISION,
            variacao_preco_pct DOUBLE PRECISION,
            kwh_por_uc_p0 DOUBLE PRECISION,
            kwh_por_uc_p1 DOUBLE PRECISION,
            periodo_p0 VARCHAR(50),
            periodo_p1 VARCHAR(50),
            _processado_em TIMESTAMP
        );
    """,
    "agg_continuidade_alimentador": """
        CREATE TABLE IF NOT EXISTS agg_continuidade_alimentador (
            alimentador VARCHAR(50),
            competencia DATE,
            total_ucs BIGINT,
            municipio_principal VARCHAR(100),
            regiao VARCHAR(50),
            alimentador_pequeno BOOLEAN,
            interrupcoes BIGINT,
            horas_x_uc DOUBLE PRECISION,
            interrupcoes_sem_dia_critico BIGINT,
            horas_x_uc_sem_dia_critico DOUBLE PRECISION,
            interrupcoes_climaticas BIGINT,
            interrupcoes_oscilacao BIGINT,
            duracoes_truncadas BIGINT,
            mes_referencia VARCHAR(20),
            ano INT,
            dec DOUBLE PRECISION,
            fec DOUBLE PRECISION,
            dec_sem_dia_critico DOUBLE PRECISION,
            fec_sem_dia_critico DOUBLE PRECISION,
            _processado_em TIMESTAMP
        );
    """,
    "agg_continuidade_alimentador_anual": """
        CREATE TABLE IF NOT EXISTS agg_continuidade_alimentador_anual (
            alimentador VARCHAR(50),
            ano INT,
            total_ucs BIGINT,
            municipio_principal VARCHAR(100),
            regiao VARCHAR(50),
            alimentador_pequeno BOOLEAN,
            interrupcoes BIGINT,
            horas_x_uc DOUBLE PRECISION,
            interrupcoes_sem_dia_critico BIGINT,
            horas_x_uc_sem_dia_critico DOUBLE PRECISION,
            interrupcoes_climaticas BIGINT,
            interrupcoes_oscilacao BIGINT,
            duracoes_truncadas BIGINT,
            meses BIGINT,
            dec DOUBLE PRECISION,
            fec DOUBLE PRECISION,
            dec_sem_dia_critico DOUBLE PRECISION,
            fec_sem_dia_critico DOUBLE PRECISION,
            rank_dec INT,
            rank_dec_sem_dia_critico INT,
            rank_impacto_horas_x_uc INT,
            _processado_em TIMESTAMP
        );
    """
}


def garantir_extracao_csvs(reset_data=False):
    """Localiza o arquivo .zip da release e descompacta na pasta data/ se necessário."""
    os.makedirs(DATA_DIR, exist_ok=True)

    if reset_data:
        print("\n-> Flag --reset-data ativada: limpando CSVs e ZIPs antigos da pasta data/...")
        for arq in glob.glob(os.path.join(DATA_DIR, "**", "*"), recursive=True):
            if os.path.isfile(arq) and (arq.endswith(".csv") or arq.endswith(".zip")):
                try:
                    os.remove(arq)
                except Exception:
                    pass
        print("-> Pasta data/ limpa com sucesso.")

    if not reset_data:
        # Procura por CSVs já existentes
        csvs = glob.glob(os.path.join(DATA_DIR, "**", "*.csv"), recursive=True)
        if csvs:
            print(f"-> Localizados {len(csvs)} arquivos CSV na pasta de dados.")
            return csvs

    # Se não houver CSVs ou se reset_data=True, procura/baixa o release mais recente
    zips = glob.glob(os.path.join(DATA_DIR, "*.zip")) + glob.glob(os.path.join(ROOT_DIR, "*.zip"))

    if not zips or reset_data:
        print("\n[!] Baixando release mais recente via GitHub CLI ('gh')...")
        try:
            subprocess.run(["gh", "release", "download", "--pattern", "*.zip", "--dir", DATA_DIR, "--clobber"], check=True)
            zips = glob.glob(os.path.join(DATA_DIR, "*.zip"))
        except Exception as e:
            print(f"    Erro ao executar 'gh release download': {e}")

    if not zips:
        print("\n[X] Arquivo .zip da release não encontrado automaticamente.")
        print(f"    Por favor, baixe o .zip da Release do GitHub e coloque em: {DATA_DIR}")
        sys.exit(1)

    zip_alvo = zips[0]
    print(f"-> Descompactando arquivo da release: {os.path.basename(zip_alvo)}...")
    with zipfile.ZipFile(zip_alvo, "r") as zf:
        zf.extractall(DATA_DIR)
    print("-> Extração concluída com sucesso.")

    csvs = glob.glob(os.path.join(DATA_DIR, "**", "*.csv"), recursive=True)
    return csvs


def mapear_arquivos_csv(csv_list):
    """Mapeia os nomes das tabelas para seus respectivos arquivos CSV."""
    mapa = {}
    for caminho in csv_list:
        nome_arquivo = os.path.basename(caminho).replace(".csv", "")
        # Normaliza nomes de tabela
        if nome_arquivo in DDL_POSTGRES:
            mapa[nome_arquivo] = caminho
    return mapa


def carregar_postgres(mapa_csv, args):
    """Executa a carga em massa ultra-rápida no PostgreSQL via comando COPY."""
    try:
        import psycopg2
    except ImportError:
        print("\n[X] Driver 'psycopg2' não encontrado.")
        print("    Para carregar no PostgreSQL, instale: pip install psycopg2-binary")
        sys.exit(1)

    url_conexao = args.url or os.getenv("DATABASE_URL")
    
    try:
        if url_conexao:
            print(f"-> Conectando ao PostgreSQL via URL...")
            conn = psycopg2.connect(url_conexao)
        else:
            print(f"-> Conectando ao PostgreSQL em {args.host}:{args.port}/{args.dbname}...")
            conn = psycopg2.connect(
                host=args.host,
                port=args.port,
                dbname=args.dbname,
                user=args.user,
                password=args.password
            )
        conn.autocommit = True
    except Exception as e:
        print(f"\n[X] Falha na conexão com PostgreSQL: {e}")
        print("\n💡 Dica: Se não tiver o Postgres rodando localmente, você pode:")
        print("   1. Subir o container Docker: docker compose up -d")
        print("   2. Ou rodar em modo SQLite: python scripts/carga_banco_local.py --sqlite")
        sys.exit(1)

    cursor = conn.cursor()
    print("-> Conectado com sucesso ao PostgreSQL!")

    # 1. Criação das tabelas
    print("\n[1/2] Verificando e criando tabelas DDL...")
    for tabela, ddl in DDL_POSTGRES.items():
        cursor.execute(f"DROP TABLE IF EXISTS {tabela} CASCADE;")
        cursor.execute(ddl)
    print("-> Esquema de tabelas validado e recriado com sucesso.")

    # 2. Carga em massa via COPY
    print("\n[2/2] Realizando carga dos dados (COPY)...")
    inicio_total = time.time()
    linhas_totais = 0

    for tabela, caminho_csv in mapa_csv.items():
        t0 = time.time()
        print(f"  • Ingerindo {tabela}...", end=" ", flush=True)
        
        # COPY nativo de alta performance com mapeamento dinâmico de colunas do cabeçalho
        with open(caminho_csv, "r", encoding="utf-8") as f:
            header_line = f.readline().strip()
            colunas_csv = [c.strip() for c in header_line.split(";")]
            colunas_sql = ", ".join(colunas_csv)
            f.seek(0)
            sql_copy = f"COPY {tabela} ({colunas_sql}) FROM STDIN WITH (FORMAT csv, DELIMITER ';', HEADER true, ENCODING 'utf-8', NULL '');"
            cursor.copy_expert(sql_copy, f)
            
        cursor.execute(f"SELECT COUNT(*) FROM {tabela};")
        qtd = cursor.fetchone()[0]
        linhas_totais += qtd
        tempo = time.time() - t0
        print(f"OK ({qtd:,} linhas em {tempo:.2f}s)")

    # 3. Data Quality Gate (Validação Automatizada)
    if not getattr(args, "skip_quality_check", False):
        print("\n[3/3] Executando Data Quality Gate...")
        res = validar_banco_postgres(cursor)
        print(f"-> Total de verificações executadas: {res.total_verificacoes}")
        if not res.sucesso:
            print("\n❌ FALHA NO DATA QUALITY GATE! A carga violou o Contrato de Dados da Gold:")
            for erro in res.erros:
                print(f"   ❌ {erro}")
            print("\n⛔ Operação abortada para proteger o Portal Web. O banco não foi liberado.")
            conn.close()
            sys.exit(1)
        print("✅ Data Quality Gate aprovado com sucesso! Nenhuma inconsistência detectada.")
    else:
        print("\n⚠️ AVISO: Data Quality Gate ignorado via flag --skip-quality-check.")

    conn.close()
    tempo_total = time.time() - inicio_total
    print(f"\n✨ Carga concluída com sucesso no PostgreSQL!")
    print(f"-> Total de linhas importadas: {linhas_totais:,}")
    print(f"-> Tempo total de processamento: {tempo_total:.2f} segundos")


def carregar_sqlite(mapa_csv, args=None):
    """Executa a carga em massa no SQLite local (data/v_energy_gold.db)."""
    import sqlite3
    import csv

    print(f"\n-> Modo SQLite ativado: gerando {SQLITE_DB_PATH}...")
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    
    # Otimizações de performance para carga massiva no SQLite
    cursor.execute("PRAGMA synchronous = OFF;")
    cursor.execute("PRAGMA journal_mode = MEMORY;")

    inicio_total = time.time()
    linhas_totais = 0

    for tabela, caminho_csv in mapa_csv.items():
        t0 = time.time()
        print(f"  • Ingerindo {tabela}...", end=" ", flush=True)
        
        with open(caminho_csv, "r", encoding="utf-8") as f:
            leitor = csv.reader(f, delimiter=";")
            cabecalho = next(leitor)
            
            # Criação dinâmica de tabela no SQLite
            cursor.execute(f"DROP TABLE IF EXISTS {tabela};")
            cols_def = ", ".join([f'"{col}" TEXT' for col in cabecalho])
            cursor.execute(f"CREATE TABLE {tabela} ({cols_def});")
            
            placeholders = ", ".join(["?"] * len(cabecalho))
            sql_insert = f"INSERT INTO {tabela} VALUES ({placeholders});"
            
            # Insere em lotes
            lote = []
            qtd = 0
            for linha in leitor:
                lote.append(linha)
                if len(lote) >= 10000:
                    cursor.executemany(sql_insert, lote)
                    qtd += len(lote)
                    lote = []
            if lote:
                cursor.executemany(sql_insert, lote)
                qtd += len(lote)
                
            conn.commit()
            linhas_totais += qtd
            tempo = time.time() - t0
            print(f"OK ({qtd:,} linhas em {tempo:.2f}s)")

    # 3. Data Quality Gate (Validação Automatizada)
    if not getattr(args, "skip_quality_check", False):
        print("\n-> Executando Data Quality Gate no SQLite...")
        res = validar_banco_sqlite(conn)
        print(f"-> Total de verificações executadas: {res.total_verificacoes}")
        if not res.sucesso:
            print("\n❌ FALHA NO DATA QUALITY GATE! A carga violou o Contrato de Dados da Gold:")
            for erro in res.erros:
                print(f"   ❌ {erro}")
            print("\n⛔ Operação abortada para proteger o Portal Web.")
            conn.close()
            if os.path.exists(SQLITE_DB_PATH):
                os.remove(SQLITE_DB_PATH)
            sys.exit(1)
        print("✅ Data Quality Gate aprovado com sucesso! Nenhuma inconsistência detectada.")
    else:
        print("\n⚠️ AVISO: Data Quality Gate ignorado via flag --skip-quality-check.")

    conn.close()
    tempo_total = time.time() - inicio_total
    print(f"\n✨ Carga concluída com sucesso no SQLite!")
    print(f"-> Arquivo do banco pronto em: {SQLITE_DB_PATH}")
    print(f"-> Total de linhas importadas: {linhas_totais:,} em {tempo_total:.2f}s")


def main():
    parser = argparse.ArgumentParser(description="Seed do Banco de Dados Local da V-Energy Grid 360")
    parser.add_argument("--sqlite", action="store_true", help="Carrega no banco SQLite local em vez do PostgreSQL")
    parser.add_argument("--skip-quality-check", action="store_true", help="Ignora a validação automatizada de qualidade de dados")
    parser.add_argument("--reset-data", "--update-release", action="store_true", dest="reset_data", help="Limpa a pasta data/ e força o download do release mais recente do GitHub")
    parser.add_argument("--url", type=str, default=None, help="Database URL (ex: postgresql://user:pass@localhost:5432/v_energy)")
    parser.add_argument("--host", type=str, default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PGPORT", 5432)))
    parser.add_argument("--dbname", type=str, default=os.getenv("PGDATABASE", "v_energy"))
    parser.add_argument("--user", type=str, default=os.getenv("PGUSER", "postgres"))
    parser.add_argument("--password", type=str, default=os.getenv("PGPASSWORD", "postgres"))

    args = parser.parse_args()

    print("=" * 70)
    print("  V-ENERGY GRID 360 · SEED DE BANCO DE DADOS LOCAL (CAMADA GOLD)")
    print("=" * 70)

    # 1. Garante extração dos CSVs
    lista_csvs = garantir_extracao_csvs(reset_data=args.reset_data)
    mapa_tabelas = mapear_arquivos_csv(lista_csvs)

    if not mapa_tabelas:
        print("\n[!] Nenhum CSV correspondente às tabelas Gold foi identificado.")
        print(f"    Arquivos encontrados: {[os.path.basename(c) for c in lista_csvs]}")
        sys.exit(1)

    print(f"-> Identificadas {len(mapa_tabelas)} tabelas para ingestão.")

    # 2. Executa a carga no destino solicitado
    if args.sqlite:
        carregar_sqlite(mapa_tabelas, args)
    else:
        carregar_postgres(mapa_tabelas, args)


if __name__ == "__main__":
    main()
