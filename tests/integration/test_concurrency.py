"""O teste mais importante do projeto: prova que o SELECT FOR UPDATE
com revalidacao pos-lock garante que dinheiro nao nasce nem some sob
concorrencia real.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.application.transfer_service import TransferService
from app.domain.exceptions import InsufficientBalanceError
from app.infrastructure.database.models import TransferModel
from app.infrastructure.database.repositories import SqlAlchemyUnitOfWork
from tests.integration.helpers import get_balance, seed_user
from tests.unit.fakes import FakeAuthorizer, FakeNotifier

pytestmark = pytest.mark.integration


def test_duas_transferencias_concorrentes_apenas_uma_conclui(session_factory):
    # payer com 100; duas transferencias SIMULTANEAS de 80 para payees diferentes
    seed_user(session_factory, 1, "100.00")
    seed_user(session_factory, 2, "0.00")
    seed_user(session_factory, 3, "0.00")

    service = TransferService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        authorizer=FakeAuthorizer(),  # sempre autoriza: aqui testamos o lock, nao a rede
        notifier=FakeNotifier(),
    )

    # sem a barreira, uma thread poderia terminar antes da outra comecar
    # e o teste passaria sem nunca ter havido concorrencia de verdade
    barrier = threading.Barrier(2)

    def attempt(payee_id: int) -> str:
        barrier.wait()
        try:
            # cada execute abre as proprias sessoes => duas transacoes reais
            service.execute(value=Decimal("80.00"), payer_id=1, payee_id=payee_id)
            return "concluida"
        except InsufficientBalanceError:
            return "recusada"

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt, 2), pool.submit(attempt, 3)]
        outcomes = sorted(future.result(timeout=30) for future in futures)

    # exatamente uma concluiu — nao zero, nao duas
    assert outcomes == ["concluida", "recusada"]
    assert get_balance(session_factory, 1) == Decimal("20.00")

    # o assert mais importante: a soma dos saldos e invariante
    # (dinheiro nao nasceu nem sumiu, independente de quem venceu a corrida)
    total = (
        get_balance(session_factory, 1)
        + get_balance(session_factory, 2)
        + get_balance(session_factory, 3)
    )
    assert total == Decimal("100.00")

    # e so a vencedora registrou historico
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(TransferModel)) == 1
