"""Escopo transacional que convive com o autobegin do SQLAlchemy."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.engine import Connection


@contextmanager
def transaction_scope(connection: Connection) -> Iterator[None]:
    """Abre a transação, ou fecha a que o autobegin já abriu na conexão.

    Com a conexão limpa é o begin() de sempre. Se uma leitura anterior já abriu
    a transação, begin() falharia; então o bloco roda nela (o SET LOCAL ROLE do
    evento "begin" já vale) e termina com commit, ou rollback se der erro.
    """
    if not connection.in_transaction():
        with connection.begin():
            yield
        return
    try:
        yield
    except BaseException:
        connection.rollback()
        raise
    connection.commit()
