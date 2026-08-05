import uuid
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from app.domain.enums import NotificationStatus, TransferStatus
from app.infrastructure.database.models import TransferModel, UserModel, WalletModel
from app.infrastructure.database.session import SessionFactory


class SqlAlchemyUsers:
    def __init__(self, session: Session):
        self._session = session

    def get(self, user_id: int) -> UserModel | None:
        return self._session.get(UserModel, user_id)


class SqlAlchemyWallets:
    def __init__(self, session: Session):
        self._session = session

    def get_balance(self, user_id: int) -> Decimal | None:
        return self._session.scalar(
            select(WalletModel.balance).where(WalletModel.user_id == user_id)
        )

    def lock_pair(self, user_id_a: int, user_id_b: int) -> dict[int, WalletModel]:
        # A query central do projeto. ORDER BY user_id garante que qualquer
        # par de transferencias adquire os locks na MESMA ordem global —
        # deadlock estruturalmente impossivel. FOR UPDATE bloqueia as linhas
        # ate o fim da transacao; quem chegar depois espera e le o saldo
        # ja atualizado.
        stmt = (
            select(WalletModel)
            .where(WalletModel.user_id.in_([user_id_a, user_id_b]))
            .order_by(WalletModel.user_id)
            .with_for_update()
        )
        wallets = self._session.scalars(stmt).all()
        return {wallet.user_id: wallet for wallet in wallets}


class SqlAlchemyTransfers:
    def __init__(self, session: Session):
        self._session = session

    def add(self, *, payer_id: int, payee_id: int, amount: Decimal) -> TransferModel:
        transfer = TransferModel(
            payer_id=payer_id,
            payee_id=payee_id,
            amount=amount,
            status=TransferStatus.COMPLETED,
            notification_status=NotificationStatus.PENDING,
        )
        self._session.add(transfer)
        self._session.flush()  # materializa id/created_at ainda dentro da transacao
        return transfer

    def set_notification_status(self, transfer_id: uuid.UUID, status: str) -> None:
        self._session.execute(
            update(TransferModel)
            .where(TransferModel.id == transfer_id)
            .values(notification_status=status)
        )


class SqlAlchemyUnitOfWork:
    """Uma unidade de trabalho = uma sessao = uma transacao.

    Sair do bloco sem commit() => rollback. E o que garante que qualquer
    erro no meio do fluxo deixa o banco exatamente como estava.
    """

    def __init__(self, session_factory: sessionmaker = SessionFactory):
        self._session_factory = session_factory

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = self._session_factory()
        self.users = SqlAlchemyUsers(self._session)
        self.wallets = SqlAlchemyWallets(self._session)
        self.transfers = SqlAlchemyTransfers(self._session)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is not None:
                self._session.rollback()
        finally:
            self._session.close()

    def commit(self) -> None:
        self._session.commit()
