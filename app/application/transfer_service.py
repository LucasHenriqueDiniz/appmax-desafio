import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.application.ports import Authorizer, Notifier, UnitOfWork
from app.domain.enums import NotificationStatus
from app.domain.exceptions import InsufficientBalanceError, UserNotFoundError
from app.domain.rules import ensure_can_transfer

logger = logging.getLogger("app.transfer")


@dataclass(frozen=True)
class TransferResult:
    id: uuid.UUID
    value: Decimal
    payer: int
    payee: int
    status: str
    notification_status: str
    created_at: datetime


class TransferService:
    """Use case da transferencia, em 4 fases.

    1. Validacoes e pre-checagem de saldo (sem transacao longa, sem locks)
    2. Autorizador externo — ANTES de abrir a transacao com locks, para
       nunca segurar lock de banco esperando rede
    3. Transacao unica: lock das duas carteiras em ordem deterministica,
       revalidacao do saldo (o mundo pode ter mudado desde a fase 1),
       debito + credito + registro da transferencia, commit
    4. Notificacao pos-commit: falha marca notification_status=failed,
       mas NUNCA reverte dinheiro ja movimentado
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        authorizer: Authorizer,
        notifier: Notifier,
    ):
        self._uow_factory = uow_factory
        self._authorizer = authorizer
        self._notifier = notifier

    def execute(self, *, value: Decimal, payer_id: int, payee_id: int) -> TransferResult:
        # FASE 1 — validacoes baratas primeiro; nada de lock ainda
        with self._uow_factory() as uow:
            payer = uow.users.get(payer_id)
            if payer is None:
                raise UserNotFoundError(f"Pagador {payer_id} nao encontrado")
            payee = uow.users.get(payee_id)
            if payee is None:
                raise UserNotFoundError(f"Beneficiario {payee_id} nao encontrado")
            ensure_can_transfer(payer, payee, value)
            balance = uow.wallets.get_balance(payer_id)
            if balance is None or balance < value:
                raise InsufficientBalanceError()

        # FASE 2 — rede fora de qualquer transacao
        self._authorizer.authorize()

        # FASE 3 — transacao unica: ou tudo acontece, ou nada acontece
        with self._uow_factory() as uow:
            wallets = uow.wallets.lock_pair(payer_id, payee_id)
            payer_wallet = wallets[payer_id]
            # revalidacao POS-LOCK: cobre a janela entre a pre-checagem/autorizacao
            # e a aquisicao do lock (outra transferencia pode ter drenado o saldo)
            if payer_wallet.balance < value:
                logger.info(
                    "transferencia recusada pos-lock: payer=%s saldo=%s valor=%s",
                    payer_id,
                    payer_wallet.balance,
                    value,
                )
                raise InsufficientBalanceError()
            payer_wallet.balance -= value
            wallets[payee_id].balance += value
            transfer = uow.transfers.add(payer_id=payer_id, payee_id=payee_id, amount=value)
            uow.commit()
            transfer_id = transfer.id
            created_at = transfer.created_at

        logger.info(
            "transferencia concluida: id=%s payer=%s payee=%s valor=%s",
            transfer_id,
            payer_id,
            payee_id,
            value,
        )

        # FASE 4 — efeito colateral pos-commit
        notification_status = self._notify(transfer_id)

        return TransferResult(
            id=transfer_id,
            value=value,
            payer=payer_id,
            payee=payee_id,
            status="completed",
            notification_status=notification_status,
            created_at=created_at,
        )

    def _notify(self, transfer_id: uuid.UUID) -> str:
        sent = self._notifier.notify()
        status = NotificationStatus.SENT if sent else NotificationStatus.FAILED
        if not sent:
            logger.warning(
                "notificacao falhou (transferencia mantida): transfer=%s", transfer_id
            )
        with self._uow_factory() as uow:
            uow.transfers.set_notification_status(transfer_id, status)
            uow.commit()
        return status
