"""Validador de SQL do agente Text-to-SQL (V-Energy Grid 360).

Camada de aplicação da defesa em profundidade (bloco "Confere o SQL" do
diagrama, requisito 5.3 de Segurança da Informação). Não substitui o
usuário de banco somente-leitura (guia_seguranca_agente.md, seção 4) nem o
statement_timeout.

Etapa 1: estrutura (parse real com SQLGlot, instrução única, raiz SELECT,
         nenhuma escrita escondida, LIMIT forçado).
Etapa 2: conteúdo (allowlist de tabelas e views `vw_gold_*`, schemas,
         funções, colunas com dado pessoal e limite de JOINs).

O agente deve executar `result.sql` (versão normalizada, sem comentários e
com LIMIT), nunca o texto original do LLM.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError
from sqlglot.optimizer.scope import traverse_scope

# --------------------------------------------------------------------------
# Configuração padrão.
# Fonte das tabelas: guia_seguranca_agente.md (seção 3, item 3), conferido
# contra data-engineering/relatorio_tabelas/dicionario_dados_gold.md (as 15
# tabelas da camada Gold). Se a Gold ganhar tabelas novas, incluir aqui.
# --------------------------------------------------------------------------

DEFAULT_ALLOWED_TABLES = frozenset(
    {
        # agregados
        "agg_continuidade_alimentador",
        "agg_continuidade_alimentador_anual",
        "agg_receita_mensal",
        "agg_receita_preco_volume",
        # dimensões
        "dim_alimentador",
        "dim_competencia",
        "dim_geracao_distribuida",
        "dim_medidor",
        "dim_unidade_consumidora",
        # fatos
        "fact_atendimentos",
        "fact_faturamento",
        "fact_inspecoes",
        "fact_leituras",
        "fact_ocorrencias",
        # fila de perdas
        "fila_inspecao",
    }
)

# Views analíticas homologadas (guia: "prefixo vw_gold_*").
DEFAULT_ALLOWED_TABLE_PREFIXES = ("vw_gold_",)

# Schemas que podem aparecer qualificados (ex.: public.fact_leituras).
DEFAULT_ALLOWED_SCHEMAS = frozenset({"public", "main"})

# Funções bloqueadas explicitamente (motivo claro no log de auditoria).
DEFAULT_BLOCKED_FUNCTIONS = frozenset(
    {
        # Postgres: DoS, leitura de arquivo, administração
        "pg_sleep", "pg_sleep_for", "pg_sleep_until",
        "pg_read_file", "pg_read_binary_file", "pg_ls_dir", "pg_stat_file",
        "pg_terminate_backend", "pg_cancel_backend",
        "pg_advisory_lock", "pg_advisory_xact_lock",
        "lo_import", "lo_export", "lo_get", "lo_put",
        "set_config", "current_setting",
        "dblink", "dblink_exec", "query_to_xml", "xpath",
        "generate_series",
        # Vazamento de informação do servidor
        "version", "current_version", "current_database", "current_user",
        "session_user", "current_schema", "inet_server_addr", "pg_backend_pid",
        # SQLite / MySQL
        "load_extension", "readfile", "writefile", "sleep", "benchmark",
    }
)

# Colunas que o agente não pode consultar.
# Dado que identifica a pessoa (LGPD "ALTO" no dicionario_dados_gold.md), em
# dim_unidade_consumidora e fila_inspecao. Latitude/longitude ficam livres: o
# dicionário as classifica como BAIXO (2 casas decimais, ~1 km). Colunas ALTO de
# comportamento (status_pagamento, dias_atraso, resultado da inspeção...) também
# ficam livres, porque as perguntas de negócio dependem delas; elas pedem política
# por perfil (ver decisoes_acoplamento_dev_genai_dados.md), não bloqueio por nome.
# Também há nomes genéricos (fonte Silver) e pseudo-colunas de usuário do banco
# (ex.: `SELECT user` no Postgres).
DEFAULT_BLOCKED_COLUMNS = frozenset(
    {
        "nome_titular", "cpf_cnpj_mascarado", "logradouro", "numero", "cep",
        "cpf_cnpj", "cpf", "cnpj", "email", "telefone", "nome_cliente", "endereco",
        "user", "current_role", "session_user", "current_user",
    }
)

# Tabelas com colunas pessoais: `SELECT *` (ou `t.*`) nelas devolveria todas as
# colunas, inclusive as bloqueadas, então o agente precisa listar as colunas.
DEFAULT_STAR_BLOCKED_TABLES = frozenset({"dim_unidade_consumidora", "fila_inspecao"})


def _node_types(*names: str) -> tuple[type, ...]:
    """Resolve classes do SQLGlot por nome (tolera diferenças de versão)."""
    return tuple(t for n in names if (t := getattr(exp, n, None)) is not None)


# Nós que nunca podem aparecer em nenhum ponto da árvore (inclusive em CTE).
_FORBIDDEN_NODES = _node_types(
    "Insert", "Update", "Delete", "Merge", "Drop", "Create", "Alter",
    "AlterTable", "TruncateTable", "Command", "Copy", "Set", "Use", "Into",
    "Lock", "Grant", "Revoke", "Transaction", "Commit", "Rollback",
    "Pragma", "Attach", "Detach", "LoadData", "Analyze", "Describe",
    "Show", "Kill", "Declare",
)

_ALLOWED_ROOTS = _node_types("Select", "Union", "Intersect", "Except")


@dataclass(frozen=True)
class ValidationResult:
    allowed: bool
    code: str  # "OK" ou o motivo do bloqueio
    reason: str  # texto legível para log/auditoria
    sql: str | None = None  # SQL normalizado (só quando allowed=True)
    tables: tuple[str, ...] = ()  # tabelas físicas referenciadas (quando conhecidas)

    def to_dict(self) -> dict:
        return asdict(self)


def _block(code: str, reason: str, tables: tuple[str, ...] = ()) -> ValidationResult:
    return ValidationResult(allowed=False, code=code, reason=reason, tables=tables)


class SQLValidator:
    def __init__(
        self,
        dialect: str = "postgres",
        allowed_tables: frozenset[str] = DEFAULT_ALLOWED_TABLES,
        allowed_table_prefixes: tuple[str, ...] = DEFAULT_ALLOWED_TABLE_PREFIXES,
        allowed_schemas: frozenset[str] = DEFAULT_ALLOWED_SCHEMAS,
        blocked_functions: frozenset[str] = DEFAULT_BLOCKED_FUNCTIONS,
        blocked_columns: frozenset[str] = DEFAULT_BLOCKED_COLUMNS,
        star_blocked_tables: frozenset[str] = DEFAULT_STAR_BLOCKED_TABLES,
        allowed_extra_functions: frozenset[str] = frozenset(),
        max_rows: int = 1000,
        max_length: int = 4000,
        max_joins: int = 8,
    ) -> None:
        self.dialect = dialect
        self.allowed_tables = frozenset(t.lower() for t in allowed_tables)
        self.allowed_table_prefixes = tuple(p.lower() for p in allowed_table_prefixes)
        self.allowed_schemas = frozenset(s.lower() for s in allowed_schemas)
        self.blocked_functions = frozenset(f.lower() for f in blocked_functions)
        self.blocked_columns = frozenset(c.lower() for c in blocked_columns)
        self.star_blocked_tables = frozenset(t.lower() for t in star_blocked_tables)
        self.allowed_extra_functions = frozenset(f.lower() for f in allowed_extra_functions)
        self.max_rows = max_rows
        self.max_length = max_length
        self.max_joins = max_joins

    def validate(self, sql: str) -> ValidationResult:
        if not isinstance(sql, str) or not sql.strip():
            return _block("EMPTY", "Consulta vazia.")
        if len(sql) > self.max_length:
            return _block("TOO_LONG", f"Consulta maior que {self.max_length} caracteres.")
        if "\x00" in sql:
            return _block("INVALID_CHARS", "Caractere nulo na consulta.")

        # 1) Parse real. Erro de sintaxe/tokenização = bloqueio.
        try:
            statements = [s for s in sqlglot.parse(sql, read=self.dialect) if s is not None]
        except SqlglotError as exc:
            return _block("PARSE_ERROR", f"SQL inválido: {str(exc).splitlines()[0][:150]}")

        if not statements:
            return _block("EMPTY", "Nenhuma instrução SQL encontrada.")
        if len(statements) > 1:
            return _block("MULTIPLE_STATEMENTS", "Apenas uma instrução SQL é permitida.")

        root = statements[0]
        while isinstance(root, exp.Subquery):  # "(SELECT ...)" -> SELECT
            root = root.this

        # 2) A raiz precisa ser SELECT (ou UNION/INTERSECT/EXCEPT de SELECTs).
        if not isinstance(root, _ALLOWED_ROOTS):
            if isinstance(root, _FORBIDDEN_NODES):
                return _block("NOT_SELECT", f"Só SELECT é permitido (recebido: {type(root).__name__}).")
            return _block("UNSUPPORTED", f"Não é uma consulta SELECT reconhecida (recebido: {type(root).__name__}).")

        # 3) Nenhum nó de escrita/administração em qualquer ponto da árvore.
        for node in root.find_all(exp.Expression):
            if isinstance(node, _FORBIDDEN_NODES):
                return _block(
                    "FORBIDDEN_NODE",
                    f"Construção não permitida dentro da consulta: {type(node).__name__}.",
                )

        # 4) Tabelas: allowlist, sem schemas de sistema, sem table functions.
        tables_or_error = self._check_tables(root)
        if isinstance(tables_or_error, ValidationResult):
            return tables_or_error
        tables = tables_or_error

        # 5) Funções: blocklist explícita + default deny para funções que o
        #    SQLGlot não modela (onde moram as funções de administração).
        for func in root.find_all(exp.Func):
            if isinstance(func, exp.Anonymous):
                fname = str(func.name).lower()
                if fname in self.blocked_functions:
                    return _block("FUNCTION_NOT_ALLOWED", f"Função bloqueada: {fname}.", tables)
                if fname not in self.allowed_extra_functions:
                    return _block("FUNCTION_UNKNOWN", f"Função não reconhecida/permitida: {fname}.", tables)
            else:
                fname = func.sql_name().lower()
                if fname in self.blocked_functions:
                    return _block("FUNCTION_NOT_ALLOWED", f"Função bloqueada: {fname}.", tables)

        # 6) Colunas bloqueadas (dado pessoal e pseudo-colunas de usuário).
        for col in root.find_all(exp.Column):
            if col.name.lower() in self.blocked_columns:
                return _block("COLUMN_NOT_ALLOWED", f"Coluna não permitida: {col.name.lower()}.", tables)

        # 6b) `SELECT *` em tabela com coluna pessoal exporia as colunas bloqueadas.
        if any(t in self.star_blocked_tables for t in tables):
            for star in root.find_all(exp.Star):
                if star.find_ancestor(exp.Count) is None:  # COUNT(*) é seguro
                    return _block(
                        "STAR_NOT_ALLOWED",
                        "Liste as colunas: SELECT * não é permitido em tabela com dado pessoal.",
                        tables,
                    )

        # 7) Limite de complexidade (proteção simples contra produto cartesiano).
        if len(list(root.find_all(exp.Join))) > self.max_joins:
            return _block("TOO_COMPLEX", f"Mais de {self.max_joins} JOINs na consulta.", tables)

        # 8) Força LIMIT (inexistente, maior que o teto ou não numérico).
        self._enforce_limit(root)

        return ValidationResult(
            allowed=True,
            code="OK",
            reason="Consulta aprovada.",
            sql=root.sql(dialect=self.dialect, comments=False),
            tables=tables,
        )

    # ------------------------------------------------------------------
    def _table_allowed(self, name: str) -> bool:
        return name in self.allowed_tables or name.startswith(self.allowed_table_prefixes)

    def _check_tables(self, root: exp.Expression) -> tuple[str, ...] | ValidationResult:
        """Confere todas as tabelas físicas. Devolve a lista ou o bloqueio."""
        nodes = list(root.find_all(exp.Table))
        for node in nodes:
            if not isinstance(node.this, exp.Identifier):
                return _block("TABLE_FUNCTION", "Funções na cláusula FROM não são permitidas.")

        # Nomes que o SQLGlot resolve como tabela física em algum escopo. Isso
        # evita que uma CTE com o mesmo nome de uma tabela proibida (ex.:
        # `WITH tb_x AS (SELECT * FROM tb_x) ...`) esconda a tabela real.
        try:
            fisicas = {
                s.name.lower()
                for scope in traverse_scope(root)
                for s in scope.sources.values()
                if isinstance(s, exp.Table)
            }
        except SqlglotError:
            return _block("PARSE_ERROR", "Não foi possível analisar o escopo da consulta.")

        cte_names = {c.alias_or_name.lower() for c in root.find_all(exp.CTE)}
        refs: list[tuple[str, str]] = []
        for node in nodes:
            name = node.name.lower()
            schema = node.db.lower() if node.db else ""
            if not schema and name in cte_names and name not in fisicas:
                continue  # referência a uma CTE, não a uma tabela
            refs.append((schema, name))

        encontradas = tuple(dict.fromkeys(name for _, name in refs))
        for schema, name in refs:
            if schema and schema not in self.allowed_schemas:
                return _block("SCHEMA_NOT_ALLOWED", f"Schema não permitido: {schema}.", encontradas)
            if not self._table_allowed(name):
                return _block("TABLE_NOT_ALLOWED", f"Tabela fora do escopo permitido: {name}.", encontradas)
        return encontradas

    def _enforce_limit(self, root: exp.Expression) -> None:
        limit = root.args.get("limit")
        if limit is None:
            root.limit(self.max_rows, copy=False)
            return
        try:
            value = int(limit.expression.name)
        except (ValueError, AttributeError):
            value = None
        if value is None or value > self.max_rows:
            root.limit(self.max_rows, copy=False)


_DEFAULT = SQLValidator()


def validate_sql(sql: str) -> ValidationResult:
    """Atalho com a configuração padrão."""
    return _DEFAULT.validate(sql)
