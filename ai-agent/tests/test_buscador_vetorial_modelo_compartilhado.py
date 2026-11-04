"""O modelo de embedding é carregado uma vez por processo, e não a cada pergunta."""
import sys
import types

import pytest

from src.rag.buscador_vetorial import BuscadorVetorial, _modelo_compartilhado


@pytest.fixture
def carregados(monkeypatch):
    """sentence_transformers falso que anota cada modelo carregado."""
    nomes: list[str] = []

    class SentenceTransformerFalso:
        def __init__(self, nome):
            nomes.append(nome)

    modulo = types.ModuleType("sentence_transformers")
    modulo.SentenceTransformer = SentenceTransformerFalso
    monkeypatch.setitem(sys.modules, "sentence_transformers", modulo)
    _modelo_compartilhado.cache_clear()
    yield nomes
    _modelo_compartilhado.cache_clear()


def test_buscadores_de_perguntas_diferentes_usam_o_mesmo_modelo(carregados):
    # O nó 5 cria um buscador novo a cada pergunta
    primeiro = BuscadorVetorial(db_url="")._carregar_modelo()
    segundo = BuscadorVetorial(db_url="")._carregar_modelo()

    assert primeiro is segundo
    assert carregados == ["paraphrase-multilingual-MiniLM-L12-v2"]


def test_outro_modelo_e_carregado_a_parte(carregados):
    BuscadorVetorial(db_url="")._carregar_modelo()
    BuscadorVetorial(db_url="", modelo_embedding="outro-modelo")._carregar_modelo()

    assert carregados == ["paraphrase-multilingual-MiniLM-L12-v2", "outro-modelo"]


def test_sem_a_biblioteca_o_erro_continua_claro(monkeypatch):
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    _modelo_compartilhado.cache_clear()

    with pytest.raises(RuntimeError, match="sentence-transformers não instalado"):
        BuscadorVetorial(db_url="")._carregar_modelo()
    _modelo_compartilhado.cache_clear()
