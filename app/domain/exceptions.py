class DomainError(Exception):
    """Base das excecoes de negocio. `code` e `message` viram o corpo do erro HTTP."""

    code = "DOMAIN_ERROR"
    message = "Erro de negocio"

    def __init__(self, message: str | None = None):
        if message is not None:
            self.message = message
        super().__init__(self.message)


class UserNotFoundError(DomainError):
    code = "USER_NOT_FOUND"
    message = "Usuario nao encontrado"


class InvalidTransferError(DomainError):
    code = "INVALID_TRANSFER"
    message = "Transferencia invalida"


class MerchantCannotTransferError(DomainError):
    code = "MERCHANT_CANNOT_TRANSFER"
    message = "Lojistas nao podem realizar transferencias, apenas receber"


class InsufficientBalanceError(DomainError):
    code = "INSUFFICIENT_BALANCE"
    message = "Saldo insuficiente para realizar a transferencia"


class TransferNotAuthorizedError(DomainError):
    code = "TRANSFER_NOT_AUTHORIZED"
    message = "Transferencia negada pelo autorizador externo"


class AuthorizerUnavailableError(DomainError):
    code = "AUTHORIZER_UNAVAILABLE"
    message = "Autorizador externo indisponivel, tente novamente mais tarde"
