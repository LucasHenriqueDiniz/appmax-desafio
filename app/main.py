from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.routes import health, transfers
from app.application.transfer_service import TransferService
from app.config import settings
from app.infrastructure.database.repositories import SqlAlchemyUnitOfWork
from app.infrastructure.integrations.authorizer import AuthorizerClient
from app.infrastructure.integrations.notifier import NotifierClient
from app.logging_config import setup_logging

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
