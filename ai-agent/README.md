# Agente Text-to-SQL

## Atualização dos insights de tela

Após mudar as consultas, os prompts ou carregar novos dados Gold, execute na pasta
`ai-agent`:

```bash
python -m scripts.gerar_insights_telas
```

O comando renova somente os quatro insights globais, usando o banco e o modelo
configurados no ambiente ou em `backend/.env.local`. Ele confirma a persistência
dos textos aprovados e informa quando houver fallback ou falha. O cache não expira
automaticamente; até a renovação, as telas podem mostrar os textos anteriores.
A Visão 360 mantém seu cache por UC e não é renovada por esse comando.

O selo de conferência verifica os números, incluindo as escalas explícitas em
campos `_mil` e `_milhoes`. Ele não certifica todas as associações semânticas da
narrativa. Confira também indicador, período, unidade e abrangência no texto
gerado; conseguir aprovação em uma ou duas rodadas é uma meta, não uma garantia.

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

## Avaliação do agente (tela do Admin TI)

A tela **Avaliação do agente** do portal mostra a evolução das métricas do golden
set (REQ-AI-08) a cada execução. Cada execução faz as perguntas de
`tests/golden_dataset/golden_dataset.json` ao agente de verdade, com o modelo e o
banco configurados no `backend/.env.local`, e grava o resultado. Na pasta `ai-agent`:

```bash
python -m scripts.avaliar_golden_set              # avalia e grava
python -m scripts.avaliar_golden_set --sem-gravar # só mostra o resultado
```

- Leva alguns minutos e gasta tokens do modelo (cerca de 100 mil por execução).
- As perguntas não entram na auditoria, então não aparecem na tela **Agente de IA**.
- A primeira execução cria as tabelas `tb_avaliacoes_agente` (uma linha por execução)
  e `tb_avaliacoes_agente_casos` (uma por caso); o setup não muda.
- As métricas e metas são as de `tests/test_avaliacao_golden_set.py`, calculadas em
  `src/avaliacao/golden_set.py`. Uma diferença: na consulta, o selo `certificada`
  também conta como executada, porque com o banco real as perguntas do cache
  certificado rodam a consulta pronta.
