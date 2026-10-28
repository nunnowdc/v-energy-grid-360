# Agente Text-to-SQL

## Testes

O guia da suíte, incluindo comandos, fixtures, uso de PostgreSQL local,
fallback SQLite, isolamento de ambiente e avaliação do Golden Dataset, está em
[`tests/README.md`](tests/README.md).

## Indexação do RAG

Para popular a base vetorial de conhecimento, execute **uma vez**:

```bash
python -m src.rag.indexar_tudo
```

> **Importante:** Rodar o indexador novamente **não duplica** os chunks — o comando é idempotente graças ao índice único em `(categoria, titulo, md5(conteudo))`.