"""Contratos (Protocols) que o use case enxerga.

A implementacao real e SQLAlchemy/httpx (infrastructure); os testes
unitarios usam fakes em memoria. E o que permite testar as regras de
negocio sem banco e sem rede.
"""

import uuid
from decimal import Decimal
from typing import Any, Protocol


class UsersPort(Protocol):
    def get(self, user_id: int) -> Any | None: ...


class WalletsPort(Protocol):
    def get_balance(self, user_id: int) -> Decimal | None: ...

    def lock_pair(self, user_id_a: int, user_id_b: int) -> dict[int, Any]:
        """Carrega as duas carteiras COM lock de escrita (SELECT FOR UPDATE),
        sempre em ordem deterministica de user_id para evitar deadlock."""
        ...


class TransfersPort(Protocol):
    def add(self, *, payer_id: int, payee_id: int, amount: Decimal) -> Any: ...

    def set_notification_status(self, transfer_id: uuid.UUID, status: str) -> None: ...


class UnitOfWork(Protocol):
    users: UsersPort
    wallets: WalletsPort
    transfers: TransfersPort

    def __enter__(self) -> "UnitOfWork": ...

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None: ...

    def commit(self) -> None: ...


class Authorizer(Protocol):
    def authorize(self) -> None:
        """Retorna silenciosamente se autorizado; levanta TransferNotAuthorizedError
        ou AuthorizerUnavailableError caso contrario."""
        ...


class Notifier(Protocol):
    def notify(self) -> bool:
        """True se a notificacao foi entregue. Nunca levanta excecao."""
        ...
