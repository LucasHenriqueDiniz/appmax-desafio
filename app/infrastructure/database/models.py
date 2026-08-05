import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.enums import NotificationStatus, TransferStatus, UserType


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("type IN ('common', 'merchant')", name="ck_users_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    document: Mapped[str] = mapped_column(String(18), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    wallet: Mapped["WalletModel"] = relationship(back_populates="user")

    @property
    def is_merchant(self) -> bool:
        return self.type == UserType.MERCHANT


class WalletModel(Base):
    """Carteira separada de users de proposito: o SELECT FOR UPDATE trava a linha
    inteira, entao o lock da transferencia atinge so o saldo, nao o cadastro.
    user_id como PK+FK torna a relacao 1-para-1 inviolavel no banco.
    """

    __tablename__ = "wallets"
    __table_args__ = (
        # defesa em profundidade: mesmo que a aplicacao falhe na validacao,
        # o banco nunca aceita saldo negativo
        CheckConstraint("balance >= 0", name="ck_wallets_balance_non_negative"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[UserModel] = relationship(back_populates="wallet")


class TransferModel(Base):
    """Historico auditavel. Criado na MESMA transacao do debito/credito:
    nao existe transferencia registrada sem o dinheiro ter se movido.
    """

    __tablename__ = "transfers"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_transfers_amount_positive"),
        CheckConstraint("payer_id <> payee_id", name="ck_transfers_distinct_users"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    payer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    payee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    status: Mapped[str] = mapped_column(String(20), default=TransferStatus.COMPLETED)
    notification_status: Mapped[str] = mapped_column(
        String(20), default=NotificationStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
