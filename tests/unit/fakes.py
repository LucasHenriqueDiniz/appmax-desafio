"""Dubles em memoria dos ports do use case: testam as regras sem banco e sem rede."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from app.domain.enums import UserType
from app.domain.exceptions import AuthorizerUnavailableError, TransferNotAuthorizedError


@dataclass
class FakeUser:
    id: int
    type: UserType = UserType.COMMON

    @property
    def is_merchant(self) -> bool:
        return self.type == UserType.MERCHANT


@dataclass
class FakeWallet:
    user_id: int
    balance: Decimal


@dataclass
class FakeTransfer:
    id: uuid.UUID
    payer_id: int
    payee_id: int
    amount: Decimal
    status: str = "completed"
    notification_status: str = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class FakeStore:
    """Estado compartilhado entre as unidades de trabalho fake."""

    def __init__(self):
        self.users: dict[int, FakeUser] = {}
        self.wallets: dict[int, FakeWallet] = {}
        self.transfers: dict[uuid.UUID, FakeTransfer] = {}

    def add_user(
        self,
        user_id: int,
        *,
        type: UserType = UserType.COMMON,  # noqa: A002
        balance: str = "0",
    ) -> None:
        self.users[user_id] = FakeUser(user_id, type)
        self.wallets[user_id] = FakeWallet(user_id, Decimal(balance))

    def balances_sum(self) -> Decimal:
        return sum((wallet.balance for wallet in self.wallets.values()), Decimal("0"))


class _FakeUsers:
    def __init__(self, store: FakeStore):
        self._store = store

    def get(self, user_id: int) -> FakeUser | None:
        return self._store.users.get(user_id)


class _FakeWallets:
    def __init__(self, store: FakeStore):
        self._store = store

    def get_balance(self, user_id: int) -> Decimal | None:
        wallet = self._store.wallets.get(user_id)
        return wallet.balance if wallet else None

    def lock_pair(self, user_id_a: int, user_id_b: int) -> dict[int, FakeWallet]:
        return {
            user_id: self._store.wallets[user_id]
            for user_id in sorted((user_id_a, user_id_b))
            if user_id in self._store.wallets
        }


class _FakeTransfers:
    def __init__(self, store: FakeStore):
        self._store = store

    def add(self, *, payer_id: int, payee_id: int, amount: Decimal) -> FakeTransfer:
        transfer = FakeTransfer(
            id=uuid.uuid4(), payer_id=payer_id, payee_id=payee_id, amount=amount
        )
        self._store.transfers[transfer.id] = transfer
        return transfer

    def set_notification_status(self, transfer_id: uuid.UUID, status: str) -> None:
        self._store.transfers[transfer_id].notification_status = status


class FakeUnitOfWork:
    def __init__(self, store: FakeStore):
        self.users = _FakeUsers(store)
        self.wallets = _FakeWallets(store)
        self.transfers = _FakeTransfers(store)

    def __enter__(self) -> "FakeUnitOfWork":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        pass

    def commit(self) -> None:
        pass


class FakeAuthorizer:
    """outcome: "ok", "denied" ou "unavailable".

    on_call permite simular o mundo mudando DURANTE a chamada de rede
    (ex.: outra transferencia drenando o saldo na janela de autorizacao).
    """

    def __init__(self, outcome: str = "ok", on_call=None):
        self.outcome = outcome
        self.on_call = on_call
        self.calls = 0

    def authorize(self) -> None:
        self.calls += 1
        if self.on_call is not None:
            self.on_call()
        if self.outcome == "denied":
            raise TransferNotAuthorizedError()
        if self.outcome == "unavailable":
            raise AuthorizerUnavailableError()


class FakeNotifier:
    def __init__(self, sent: bool = True):
        self.sent = sent
        self.calls = 0

    def notify(self) -> bool:
        self.calls += 1
        return self.sent
