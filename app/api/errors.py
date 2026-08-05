import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    AuthorizerUnavailableError,
    DomainError,
    InsufficientBalanceError,
    InvalidTransferError,
    MerchantCannotTransferError,
    TransferNotAuthorizedError,
    UserNotFoundError,
)

# 422: a requisicao em si viola uma regra (independe de estado)
# 409: conflito com o estado atual (pode funcionar amanha)
# 403: somente negacao do autorizador externo
# 503: dependencia indisponivel — na duvida, dinheiro nao se move
STATUS_BY_EXCEPTION: dict[type[DomainError], int] = {
    UserNotFoundError: 404,
    InvalidTransferError: 422,
    MerchantCannotTransferError: 422,
    InsufficientBalanceError: 409,
    TransferNotAuthorizedError: 403,
    AuthorizerUnavailableError: 503,
}


logger = logging.getLogger("app.api")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        status_code = STATUS_BY_EXCEPTION.get(type(exc), 500)
        # uma linha por recusa: para quem opera o sistema, as recusas
        # sao metade da historia — nao so as transferencias concluidas
        logger.info(
            "requisicao recusada: code=%s status=%s path=%s",
            exc.code,
            status_code,
            request.url.path,
        )
        return JSONResponse(
            status_code=status_code,
            content={"code": exc.code, "message": exc.message},
        )
