"""Prova que a fronteira transacional esta certa: falha no meio da
operacao => rollback do Postgres => nenhum saldo muda, nenhum registro fica.
"""

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.application.transfer_service import TransferService
from app.infrastructure.database.models import TransferModel
from app.infrastructure.database.repositories import SqlAlchemyUnitOfWork
from tests.integration.helpers import get_balance, seed_user
from tests.unit.fakes import FakeAuthorizer, FakeNotifier

pytestmark = pytest.mark.integration


class _ExplodingTransfers:
    """Simula um crash DEPOIS do debito e do credito, antes do commit."""

    def add(self, **kwargs):
        raise RuntimeError("falha injetada entre o debito/credito e o registro")


class _ExplodingUnitOfWork(SqlAlchemyUnitOfWork):
    def __enter__(self):
        super().__enter__()
        self.transfers = _ExplodingTransfers()
        return self


def test_falha_no_meio_da_transacao_nao_deixa_dinheiro_pela_metade(session_factory):
    seed_user(session_factory, 1, "100.00")
    seed_user(session_factory, 2, "0.00")

    service = TransferService(
        uow_factory=lambda: _ExplodingUnitOfWork(session_factory),
        authorizer=FakeAuthorizer(),
        notifier=FakeNotifier(),
    )

    with pytest.raises(RuntimeError, match="falha injetada"):
        service.execute(value=Decimal("80.00"), payer_id=1, payee_id=2)

    # o debito e o credito ja tinham sido aplicados na sessao quando a falha
    # ocorreu — o rollback desfez os dois juntos; nada ficou pela metade
    assert get_balance(session_factory, 1) == Decimal("100.00")
    assert get_balance(session_factory, 2) == Decimal("0.00")
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(TransferModel)) == 0
