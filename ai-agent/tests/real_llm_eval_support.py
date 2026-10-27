"""Strict OpenRouter client and privacy guards for the opt-in live evaluation."""
from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urlparse

import sqlglot
from sqlglot import exp

from ai_agent.src.interfaces.validador_sql_interface import ResultadoValidacaoSQL
from ai_agent.src.provedores.cliente_llm import ClienteLLM, RespostaLLM
from ai_agent.src.services.sql_executor import ResultadoExecucaoSQL, SQLExecutor
from security.sql_validator import DEFAULT_BLOCKED_COLUMNS, SQLValidator

MAX_OPENROUTER_CALLS = 60
MIN_GROUP_SIZE = 10
INSTRUCAO_PRIVACIDADE_SQL = """
REQUISITOS ADICIONAIS DESTA AVALIAÇÃO:
- Retorne somente métricas agregadas; nunca retorne linhas de clientes ou valores
  individuais.
- Não projete identificadores, nomes, documentos, endereços ou outros dados
  pessoais.
- Inclua COUNT(DISTINCT id_uc), COUNT(*) ou SUM(ucs_faturadas) com alias
  sample_size. Em cada grupo, sample_size deve representar ao menos 10 UCs ou
  registros. Caso contrário, retorne SQL_INDISPONIVEL.
- Agrupe somente por dimensões seguras, como município, bairro, classe, ano,
  mês, competência, causa ou tipo.
""".strip()

TABELAS_GOLD_AVALIACAO = frozenset(
    {
        "agg_receita_mensal",
        "dim_unidade_consumidora",
        "fact_faturamento",
        "fact_leituras",
        "fact_ocorrencias",
    }
)

COLUNAS_DE_GRUPO_SEGURAS = frozenset(
    {"bairro", "causa", "classe", "competencia", "mes", "municipio", "tipo", "ano"}
)
COLUNAS_METRICAS_AGREGAVEIS = frozenset(
    {
        "consumo_kwh",
        "duracao_h",
        "receita_faturada",
        "receita_recebida",
        "ucs_faturadas",
    }
)
COLUNAS_IDENTIFICADORAS = frozenset(
    {
        "id_fatura",
        "id_inspecao",
        "id_leitura",
        "id_medidor",
        "id_ocorrencia",
        "id_uc",
        "protocolo",
    }
)
COLUNAS_PESSOAIS = frozenset(
    {
        "cpf_cnpj_mascarado",
        "email",
        "latitude",
        "longitude",
        "logradouro",
        "nome_titular",
        "numero",
        "telefone",
        "cep",
    }
)


class ErroAvaliacaoLLM(RuntimeError):
    """Falha de configuração, segurança ou orçamento na avaliação com LLM real."""


class ClienteOpenRouterLimitado(ClienteLLM):
    """Cliente de teste que aceita apenas OpenRouter e limita chamadas externas."""

    def __init__(
        self,
        limite_chamadas: int = MAX_OPENROUTER_CALLS,
        modelo: str | None = None,
    ) -> None:
        super().__init__(modelo_primario=modelo)
        if not self.openrouter_key:
            raise ErroAvaliacaoLLM(
                "Defina OPENROUTER_API_KEY para executar a avaliação real."
            )
        if urlparse(self.openrouter_url).hostname != "openrouter.ai":
            raise ErroAvaliacaoLLM(
                "A avaliação real exige conexão direta ao host openrouter.ai."
            )
        if self.forcar_mock:
            raise ErroAvaliacaoLLM(
                "LLM_MOCK_MODE está ativo; desative-o para exigir chamadas ao OpenRouter."
            )
        if limite_chamadas < 1:
            raise ValueError("limite_chamadas deve ser positivo.")

        self.limite_chamadas = limite_chamadas
        self.chamadas_openrouter = 0
        self.tokens_prompt = 0
        self.tokens_resposta = 0
        self.erro_fatal: str | None = None
        self.ninerouter_key = ""

    def invoke(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperatura: float = 0.0,
        resposta_mock: str | None = None,
    ) -> RespostaLLM:
        if system_prompt and "especialista em sql" in system_prompt.lower():
            system_prompt = f"{system_prompt}\n\n{INSTRUCAO_PRIVACIDADE_SQL}"
        mensagens = []
        if system_prompt:
            mensagens.append({"role": "system", "content": system_prompt})
        mensagens.append({"role": "user", "content": prompt})

        inicio = time.time()
        try:
            resposta = self._chamar_api(
                url=self.openrouter_url,
                api_key=self.openrouter_key,
                modelo=self.modelo_primario,
                mensagens=mensagens,
                temperatura=temperatura,
            )
        except Exception as exc:
            if not self.erro_fatal:
                self.erro_fatal = "Falha na chamada OpenRouter."
            raise ErroAvaliacaoLLM(self.erro_fatal) from exc

        resposta.provedor_utilizado = "openrouter"
        resposta.latencia_ms = (time.time() - inicio) * 1000
        self.tokens_prompt += resposta.tokens_prompt
        self.tokens_resposta += resposta.tokens_resposta
        return resposta

    def _chamar_api(
        self,
        url: str,
        api_key: str,
        modelo: str,
        mensagens: list[dict[str, str]],
        temperatura: float,
    ) -> RespostaLLM:
        if url != self.openrouter_url or api_key != self.openrouter_key:
            self.erro_fatal = "A avaliação permite chamadas somente ao OpenRouter."
            raise ErroAvaliacaoLLM(self.erro_fatal)
        if self.chamadas_openrouter >= self.limite_chamadas:
            self.erro_fatal = (
                f"Limite de {self.limite_chamadas} chamadas OpenRouter atingido."
            )
            raise ErroAvaliacaoLLM(self.erro_fatal)

        self.chamadas_openrouter += 1
        try:
            return super()._chamar_api(
                url=url,
                api_key=api_key,
                modelo=modelo,
                mensagens=mensagens,
                temperatura=temperatura,
            )
        except Exception as exc:
            self.erro_fatal = "A chamada ao OpenRouter falhou."
            raise ErroAvaliacaoLLM(self.erro_fatal) from exc


class ValidadorSQLAgregadoGold:
    """Permite só SELECTs Gold com projeções agregadas e dimensões seguras."""

    def __init__(self) -> None:
        self.violacoes_sql_inseguro: list[str] = []
        self.rejeicoes_sem_prova_amostral = 0
        self._validador = SQLValidator(
            dialect="postgres",
            allowed_tables=TABELAS_GOLD_AVALIACAO,
            allowed_table_prefixes=(),
            blocked_columns=DEFAULT_BLOCKED_COLUMNS,
            max_rows=50,
        )

    def validar(self, sql: str) -> ResultadoValidacaoSQL:
        validacao = self._validador.validate(sql)
        if not validacao.allowed:
            inseguro = validacao.code in {
                "COLUMN_NOT_ALLOWED",
                "FORBIDDEN_NODE",
                "FUNCTION_NOT_ALLOWED",
                "FUNCTION_UNKNOWN",
                "MULTIPLE_STATEMENTS",
                "NOT_SELECT",
                "SCHEMA_NOT_ALLOWED",
                "TABLE_FUNCTION",
                "TABLE_NOT_ALLOWED",
            }
            if inseguro:
                self.violacoes_sql_inseguro.append(validacao.reason)
            return ResultadoValidacaoSQL(
                aprovado=False,
                motivo_rejeicao=validacao.reason,
                malicioso=inseguro,
                tabelas_detectadas=list(validacao.tables),
            )

        try:
            arvore = sqlglot.parse_one(sql, read="postgres")
        except sqlglot.errors.SqlglotError as exc:
            return self._rejeitar(f"SQL inválido: {exc}")

        if not isinstance(arvore, exp.Select) or arvore.find(exp.Subquery) or arvore.find(exp.CTE):
            return self._rejeitar(
                "A avaliação real permite apenas um SELECT simples, sem subconsultas ou CTEs.",
                list(validacao.tables),
            )
        if any(isinstance(projecao.this if isinstance(projecao, exp.Alias) else projecao, exp.Star)
               for projecao in arvore.expressions):
            return self._rejeitar(
                "SELECT * não é permitido na avaliação com dados Gold.",
                list(validacao.tables),
                malicioso=True,
            )

        for coluna in arvore.find_all(exp.Column):
            nome = coluna.name.lower()
            if nome in COLUNAS_PESSOAIS:
                return self._rejeitar(
                    "A consulta acessa coluna com dado pessoal.",
                    list(validacao.tables),
                    malicioso=True,
                )
            if nome not in COLUNAS_IDENTIFICADORAS:
                continue
            if nome == "id_uc" and (
                _coluna_usada_em_contagem_distinta(coluna)
                or _coluna_usada_em_juncao(coluna, arvore)
            ):
                continue
            return self._rejeitar(
                "A consulta acessa coluna identificadora fora de junção ou contagem distinta.",
                list(validacao.tables),
                malicioso=True,
            )

        group = arvore.args.get("group")
        colunas_grupo = {
            coluna.name.lower()
            for coluna in group.find_all(exp.Column)
        } if group else set()
        if not colunas_grupo.issubset(COLUNAS_DE_GRUPO_SEGURAS):
            return self._rejeitar(
                "O GROUP BY contém coluna não autorizada para dados agregados.",
                list(validacao.tables),
                malicioso=True,
            )

        possui_amostra = False
        for projecao in arvore.expressions:
            expressao = projecao.this if isinstance(projecao, exp.Alias) else projecao
            alias = (
                projecao.alias.lower()
                if isinstance(projecao, exp.Alias)
                else ""
            )
            if alias == "sample_size" and _expressao_tamanho_amostra(expressao):
                possui_amostra = True

            if isinstance(expressao, exp.Column):
                if (
                    expressao.name.lower() not in COLUNAS_DE_GRUPO_SEGURAS
                    or expressao.name.lower() not in colunas_grupo
                ):
                    return self._rejeitar(
                        "A saída SQL contém uma coluna não agregada ou identificadora.",
                        list(validacao.tables),
                        malicioso=True,
                    )
                continue

            if not any(isinstance(no, exp.AggFunc) for no in expressao.walk()):
                return self._rejeitar(
                    "Todas as saídas devem ser métricas agregadas ou dimensões seguras.",
                    list(validacao.tables),
                    malicioso=True,
                )

            for coluna in expressao.find_all(exp.Column):
                nome = coluna.name.lower()
                if nome in COLUNAS_IDENTIFICADORAS:
                    if nome != "id_uc" or not _coluna_usada_em_contagem_distinta(coluna):
                        return self._rejeitar(
                            "Identificadores só podem ser usados em COUNT(DISTINCT id_uc), nunca como saída.",
                            list(validacao.tables),
                            malicioso=True,
                        )
                elif nome not in COLUNAS_METRICAS_AGREGAVEIS:
                    return self._rejeitar(
                        f"A métrica agregada usa coluna não autorizada: {nome}.",
                        list(validacao.tables),
                        malicioso=True,
                    )

        if not possui_amostra:
            return self._rejeitar(
                "Inclua COUNT(DISTINCT id_uc), COUNT(*) ou SUM(ucs_faturadas) "
                "com alias sample_size para provar pelo menos 10 registros por grupo.",
                list(validacao.tables),
            )

        return ResultadoValidacaoSQL(
            aprovado=True,
            motivo_rejeicao=None,
            malicioso=False,
            tabelas_detectadas=list(validacao.tables),
        )

    def _rejeitar(
        self,
        motivo: str,
        tabelas: list[str] | None = None,
        malicioso: bool = False,
    ) -> ResultadoValidacaoSQL:
        if malicioso:
            self.violacoes_sql_inseguro.append(motivo)
        if "sample_size" in motivo.lower():
            self.rejeicoes_sem_prova_amostral += 1
        return ResultadoValidacaoSQL(
            aprovado=False,
            motivo_rejeicao=motivo,
            malicioso=malicioso,
            tabelas_detectadas=tabelas or [],
        )


def _expressao_tamanho_amostra(expressao: exp.Expression) -> bool:
    if isinstance(expressao, exp.Count):
        return True
    return (
        isinstance(expressao, exp.Sum)
        and any(
            isinstance(coluna, exp.Column)
            and coluna.name.lower() == "ucs_faturadas"
            for coluna in expressao.find_all(exp.Column)
        )
    )


def _coluna_usada_em_contagem_distinta(coluna: exp.Column) -> bool:
    no: exp.Expression | None = coluna
    while no is not None and not isinstance(no, exp.Count):
        no = no.parent
    if not isinstance(no, exp.Count):
        return False
    return isinstance(no.this, exp.Distinct)


def _coluna_usada_em_juncao(
    coluna: exp.Column,
    arvore: exp.Expression,
) -> bool:
    return any(
        join.args.get("on") is not None
        and any(coluna is coluna_juncao for coluna_juncao in join.args["on"].find_all(exp.Column))
        for join in arvore.find_all(exp.Join)
    )


class ExecutorGoldAgregado:
    """Filtra resultados sem prova de tamanho mínimo antes da síntese do LLM."""

    def __init__(
        self,
        executor: SQLExecutor,
        validador: ValidadorSQLAgregadoGold,
        tamanho_minimo: int = MIN_GROUP_SIZE,
    ) -> None:
        if tamanho_minimo < 1:
            raise ValueError("tamanho_minimo deve ser positivo.")
        self._executor = executor
        self._validador = validador
        self._tamanho_minimo = tamanho_minimo
        self.grupos_suprimidos = 0

    def executar(
        self,
        sql: str,
        limite_linhas: int = 50,
    ) -> ResultadoExecucaoSQL:
        validacao = self._validador.validar(sql)
        if not validacao.aprovado:
            return ResultadoExecucaoSQL(
                sucesso=False,
                erro=validacao.motivo_rejeicao,
            )

        resultado = self._executor.executar(sql, limite_linhas=limite_linhas)
        if not resultado.sucesso or not resultado.linhas:
            return resultado

        linhas_seguras: list[dict[str, Any]] = []
        for linha in resultado.linhas:
            chave_amostra = next(
                (
                    chave
                    for chave in linha
                    if chave.lower() == "sample_size"
                ),
                None,
            )
            if chave_amostra is None:
                return ResultadoExecucaoSQL(
                    sucesso=False,
                    erro="A consulta não retornou sample_size; resultado não compartilhado.",
                    tempo_execucao_ms=resultado.tempo_execucao_ms,
                )
            try:
                tamanho = int(linha[chave_amostra])
            except (TypeError, ValueError, OverflowError):
                return ResultadoExecucaoSQL(
                    sucesso=False,
                    erro="sample_size inválido; resultado não compartilhado.",
                    tempo_execucao_ms=resultado.tempo_execucao_ms,
                )
            if tamanho >= self._tamanho_minimo:
                linhas_seguras.append(linha)

        self.grupos_suprimidos += len(resultado.linhas) - len(linhas_seguras)
        return ResultadoExecucaoSQL(
            sucesso=True,
            linhas=linhas_seguras,
            total_linhas=len(linhas_seguras),
            tempo_execucao_ms=resultado.tempo_execucao_ms,
        )


def validacao_execucao_real_habilitada() -> bool:
    return os.getenv("AI_AGENT_RUN_REAL_LLM", "").strip().lower() in {"1", "true", "yes"}
