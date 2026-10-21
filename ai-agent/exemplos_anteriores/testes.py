import sqlite3 #Aqui vamos usar para Cria um banco de dados temporário para os testes
import pytest #vamos usar para testes parametrizados e fixtures
from services.sql_executor import SQLSecurityError, execute_readonly_query, validate_readonly_sql
    
@pytest.fixture
def tmp_db(tmp_path):
    db_path = tmp_path / "test.db"
    connection = sqlite3.connect(str(db_path))
    connection.execute(
        "CREATE TABLE dim_movies (sk_movie_id TEXT PRIMARY KEY, titulo TEXT, ano_lancamento INTEGER)"
    )
    connection.execute("INSERT INTO dim_movies VALUES ('abc', 'Test Movie', 2020)")
    connection.commit()
    connection.close()
    return str(db_path)

#testando o caminho feliz (queries válidas)
@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM dim_movies",
        "SELECT titulo FROM dim_movies WHERE ano_lancamento > 2000",
        "WITH recentes AS (SELECT * FROM dim_movies) SELECT * FROM recentes",
        "SELECT titulo FROM dim_movies UNION SELECT titulo FROM dim_movies",
    ],
)
def test_valid_select_passes(sql):
    validate_readonly_sql(sql)  # não deve levantar exceção

#testando o bad ending
@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE dim_movies",
        "DELETE FROM dim_movies",
        "UPDATE dim_movies SET titulo = 'x'",
        "INSERT INTO dim_movies VALUES ('y', 'Hack', 2024)",
        "PRAGMA table_info(dim_movies)",
        "ATTACH DATABASE 'outro.db' AS outro",
        "SELECT * FROM dim_movies; DROP TABLE dim_movies",
        "",
        "   ",
    ],
)
def test_dangerous_or_invalid_sql_blocked(sql):
    with pytest.raises(SQLSecurityError):
        validate_readonly_sql(sql)

#Falsos positivos

def test_semicolon_inside_string_literal_not_falsely_blocked():
    # regressão: um ';' dentro de um valor literal não pode ser confundido
    # com instruções encadeadas, o parser entende aspas, uma checagem
    # ingênua de string ("in sql") não entenderia
    sql = "SELECT * FROM dim_movies WHERE titulo = 'Colon: Test; The Movie'"
    validate_readonly_sql(sql)  # não deve levantar exceção

#executando
def test_execute_readonly_query(tmp_db):
    result = execute_readonly_query("SELECT titulo FROM dim_movies", tmp_db)
    assert result.row_count == 1
    assert result.columns == ["titulo"]
    assert result.rows == [["Test Movie"]]

#tESTe da camada limit
def test_execute_readonly_query_applies_row_limit(tmp_db):
    result = execute_readonly_query("SELECT * FROM dim_movies", tmp_db, max_rows=0)
    assert result.row_count == 0

#Teste de erro de sintaxe: coluna inexistente
def test_execute_readonly_query_raises_on_missing_column(tmp_db):
    with pytest.raises(sqlite3.OperationalError):
        execute_readonly_query("SELECT non_existent_column FROM dim_movies", tmp_db)

#testando ultimo recurso
def test_readonly_connection_blocks_write_even_if_validation_is_bypassed(tmp_db):
    # mesmo que a validação seja ignorada, a conexão em modo somente leitura
    # deve impedir qualquer operação de escrita
    with pytest.raises(sqlite3.OperationalError):
        with sqlite3.connect(f"file:{tmp_db}?mode=ro", uri=True) as connection:
            connection.execute("DELETE FROM dim_movies")