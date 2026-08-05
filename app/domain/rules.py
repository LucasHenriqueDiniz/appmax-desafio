from decimal import Decimal
from typing import Protocol

from app.domain.exceptions import InvalidTransferError, MerchantCannotTransferError


class UserLike(Protocol):
    id: int
    is_merchant: bool


def ensure_can_transfer(payer: UserLike, payee: UserLike, value: Decimal) -> None:
    """Regras de negocio da transferencia, independentes de banco e HTTP."""
    if value <= 0:
        raise InvalidTransferError("O valor da transferencia deve ser maior que zero")
    if payer.id == payee.id:
        raise InvalidTransferError("Pagador e beneficiario devem ser usuarios diferentes")
    if payer.is_merchant:
        raise MerchantCannotTransferError()
