import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.api.errors import register_exception_handlers
from app.api.routes import health, transfers
from app.application.transfer_service import TransferService
from app.config import settings
from app.infrastructure.database.repositories import SqlAlchemyUnitOfWork
from app.infrastructure.integrations.authorizer import AuthorizerClient
from app.infrastructure.integrations.notifier import NotifierClient
from app.logging_config import setup_logging
from app.request_context import request_id_var

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # clientes criados uma unica vez (reuso de conexoes) e fechados no shutdown
    authorizer = AuthorizerClient(settings.authorizer_url, settings.external_timeout_seconds)
    notifier = NotifierClient(settings.notifier_url, settings.external_timeout_seconds)
    app.state.transfer_service = TransferService(
        uow_factory=SqlAlchemyUnitOfWork,
        authorizer=authorizer,
        notifier=notifier,
    )
    yield
    authorizer.close()
    notifier.close()


app = FastAPI(title="API de Transferencias — Desafio Appmax", lifespan=lifespan)
register_exception_handlers(app)
app.include_router(health.router)
app.include_router(transfers.router)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Um id curto por requisicao: correlaciona todas as linhas de log
    de uma mesma transferencia sob concorrencia, e volta no header
    X-Request-ID para o cliente citar em suporte/debug."""
    request_id = uuid.uuid4().hex[:8]
    token = request_id_var.set(request_id)
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)
    response.headers["X-Request-ID"] = request_id
    return response
