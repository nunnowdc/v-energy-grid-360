"""
Testes: a conta e o perfil de quem perguntou chegam ao registro de auditoria.
No portal, os dois vêm da sessão (ai_router.usuario_logado).
"""
from __future__ import annotations

from src.grafo.construtor_grafo import _inicializar_estado
from src.nos import no_finaliza_auditoria as modulo_auditoria

USUARIO = "6f1c2b8e-1d2a-4c3b-9e8f-0a1b2c3d4e5f"


def test_estado_inicial_guarda_usuario_e_perfil():
    estado = _inicializar_estado(
        pergunta="Qual a receita?", historico=None, sessao_id="s1", user_id=USUARIO, perfil="DIRETORIA"
    )

    assert estado["user_id"] == USUARIO
    assert estado["perfil"] == "DIRETORIA"


def test_estado_inicial_sem_usuario_nao_inventa_um():
    estado = _inicializar_estado(pergunta="Qual a receita?", historico=None, sessao_id="s1")

    assert "user_id" not in estado
    assert "perfil" not in estado


def test_auditoria_grava_usuario_e_perfil(monkeypatch):
    gravados = []
    monkeypatch.setattr(modulo_auditoria, "_gravar_auditoria", lambda registro, _db_url: gravados.append(registro))
    estado = _inicializar_estado(
        pergunta="Qual a receita?", historico=None, sessao_id="s1", user_id=USUARIO, perfil="DIRETORIA"
    )

    modulo_auditoria.no_finaliza_auditoria(estado, db_url=None)

    assert gravados[0]["user_id"] == USUARIO
    assert gravados[0]["perfil"] == "DIRETORIA"
