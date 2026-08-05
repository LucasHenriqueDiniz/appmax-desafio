"""Correlacao de logs: um id curto por requisicao, propagado via contextvar.

Contextvars atravessam o threadpool do FastAPI (o anyio copia o contexto),
entao qualquer log emitido durante a requisicao — rota, use case,
clientes HTTP — carrega o mesmo id sem passar parametro nenhum.
"""

import contextvars

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
