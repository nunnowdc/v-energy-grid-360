#!/usr/bin/env python
"""
Migração: liga a auditoria do agente à conta que fez a pergunta (idempotente).

- user_id vira UUID com chave estrangeira para usuarios(id). Registros antigos
  sem um id de conta válido (de antes do login) ficam com user_id NULL.
- Índice por usuário e data, para consultar o histórico de uma conta.

Precisa da tabela usuarios (passo 7.2 do README). Por isso roda depois dela,
e não junto da migracao_colunas_opcionais_auditoria_agente.

Sem ON DELETE: a auditoria não pode perder o autor, então uma conta com
perguntas no histórico não pode ser apagada (o portal não apaga contas).

Execute:
  python -m scripts.migracoes.migracao_usuario_auditoria_agente
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

# Carrega .env da raiz do projeto
RAIZ = Path(__file__).resolve().parents[3]
load_dotenv(RAIZ / ".env")

REGEX_UUID = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
NOME_FK = "tb_auditoria_agente_user_id_fkey"


def _sem_url(texto: str) -> str:
    """Esconde URLs de banco (com a senha) que o driver põe em algumas mensagens."""
    return re.sub(r"postgres[a-z+]*://\S+", "postgresql://***", texto)


def aplicar(cur) -> int:
    """Aplica a migração no cursor aberto e devolve quantos registros ficaram sem usuário."""
    # As colunas vêm da migração das colunas opcionais; garante aqui para não depender dela
    cur.execute("ALTER TABLE tb_auditoria_agente ADD COLUMN IF NOT EXISTS user_id VARCHAR(100);")
    cur.execute("ALTER TABLE tb_auditoria_agente ADD COLUMN IF NOT EXISTS perfil VARCHAR(50);")

    sem_usuario = 0
    cur.execute(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_schema = current_schema() "
        "AND table_name = 'tb_auditoria_agente' AND column_name = 'user_id';"
    )
    if cur.fetchone()[0] != "uuid":
        # Ids de teste em texto (de antes do login) não viram UUID: ficam vazios
        cur.execute(
            "UPDATE tb_auditoria_agente SET user_id = NULL "
            "WHERE user_id IS NOT NULL AND user_id !~* %s;",
            (REGEX_UUID,),
        )
        sem_usuario += cur.rowcount
        cur.execute(
            "ALTER TABLE tb_auditoria_agente ALTER COLUMN user_id TYPE UUID USING user_id::uuid;"
        )

    # UUID de uma conta que não existe mais (ou nunca existiu) também fica vazio
    cur.execute(
        "UPDATE tb_auditoria_agente AS a SET user_id = NULL "
        "WHERE a.user_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM usuarios AS u WHERE u.id = a.user_id);"
    )
    sem_usuario += cur.rowcount

    cur.execute("SELECT 1 FROM pg_constraint WHERE conname = %s;", (NOME_FK,))
    if cur.fetchone() is None:
        cur.execute(
            f"ALTER TABLE tb_auditoria_agente ADD CONSTRAINT {NOME_FK} "
            "FOREIGN KEY (user_id) REFERENCES usuarios (id);"
        )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_auditoria_usuario "
        "ON tb_auditoria_agente (user_id, data_hora DESC);"
    )
    return sem_usuario


def main() -> int:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌  DATABASE_URL não definida no .env")
        return 1

    try:
        import psycopg2
    except ImportError:
        print("❌  psycopg2-binary não instalado. Execute: pip install psycopg2-binary")
        return 1

    print("🔧  Aplicando migração: usuário da auditoria como chave estrangeira...")

    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT to_regclass('public.usuarios') IS NOT NULL, "
                    "to_regclass('public.tb_auditoria_agente') IS NOT NULL;"
                )
                tem_usuarios, tem_auditoria = cur.fetchone()
                if not tem_auditoria:
                    print("❌  Falta a tabela tb_auditoria_agente. Rode antes: python scripts/criar_tabelas_ia.py")
                    return 1
                if not tem_usuarios:
                    print("❌  Falta a tabela usuarios. Rode antes o passo 7.2 do README (ou o setup).")
                    return 1
                sem_usuario = aplicar(cur)
            conn.commit()

        if sem_usuario:
            print(f"   {sem_usuario} registro(s) antigo(s) sem conta válida ficaram com user_id vazio.")
        print("✅  Migração concluída com sucesso.")
        return 0

    except Exception as e:
        print(f"❌  Erro ao aplicar migração: {_sem_url(str(e))}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
