"""Testes das regras criticas do use case, com fakes em memoria.

Cada teste prova uma decisao de design. O invariante que aparece em
todos: quando a transferencia nao acontece, NADA muda no estado.
"""

from decimal import Decimal

import pytest

from app.application.transfer_service import TransferService
from app.domain.enums import UserType
from app.domain.exceptions import (
    AuthorizerUnavailableError,
    InsufficientBalanceError,
    InvalidTransferError,
    MerchantCannotTransferError,
    TransferNotAuthorizedError,
    UserNotFoundError,
)
from tests.unit.fakes import FakeAuthorizer, FakeNotifier, FakeStore, FakeUnitOfWork


def make_service(store, authorizer=None, notifier=None):
    return TransferService(
        uow_factory=lambda: FakeUnitOfWork(store),
        authorizer=authorizer or FakeAuthorizer(),
        notifier=notifier or FakeNotifier(),
    )


@pytest.fixture
def store():
    s = FakeStore()
    s.add_user(1, balance="100.00")
    s.add_user(2, balance="50.00")
    s.add_user(9, type=UserType.MERCHANT, balance="10.00")
    return s


def test_transferencia_concluida_move_o_dinheiro_e_registra(store):
    result = make_service(store).execute(value=Decimal("40.00"), payer_id=1, payee_id=2)

    assert store.wallets[1].balance == Decimal("60.00")
    assert store.wallets[2].balance == Decimal("90.00")
    assert result.status == "completed"
    assert result.notification_status == "sent"
    assert len(store.transfers) == 1
    assert store.balances_sum() == Decimal("160.00")


def test_usuario_comum_pode_transferir_para_lojista(store):
    make_service(store).execute(value=Decimal("10.00"), payer_id=1, payee_id=9)

    assert store.wallets[9].balance == Decimal("20.00")


def test_lojista_nao_pode_ser_pagador(store):
    authorizer = FakeAuthorizer()

    with pytest.raises(MerchantCannotTransferError):
        make_service(store, authorizer).execute(value=Decimal("5.00"), payer_id=9, payee_id=1)

    assert store.wallets[9].balance == Decimal("10.00")
    assert len(store.transfers) == 0
    assert authorizer.calls == 0  # falha barata primeiro: nem chama a rede


def test_saldo_insuficiente_recusa_antes_do_autorizador(store):
    authorizer = FakeAuthorizer()

    with pytest.raises(InsufficientBalanceError):
        make_service(store, authorizer).execute(value=Decimal("100.01"), payer_id=1, payee_id=2)

    assert store.wallets[1].balance == Decimal("100.00")
    assert authorizer.calls == 0


def test_valor_zero_ou_negativo_e_invalido(store):
    service = make_service(store)

    for value in (Decimal("0"), Decimal("-10.00")):
        with pytest.raises(InvalidTransferError):
            service.execute(value=value, payer_id=1, payee_id=2)

    assert store.wallets[1].balance == Decimal("100.00")


def test_pagador_igual_ao_beneficiario_e_invalido(store):
    with pytest.raises(InvalidTransferError):
        make_service(store).execute(value=Decimal("10.00"), payer_id=1, payee_id=1)


def test_pagador_ou_beneficiario_inexistente(store):
    service = make_service(store)

    with pytest.raises(UserNotFoundError):
        service.execute(value=Decimal("10.00"), payer_id=999, payee_id=2)
    with pytest.raises(UserNotFoundError):
        service.execute(value=Decimal("10.00"), payer_id=1, payee_id=999)


def test_autorizacao_negada_nao_move_dinheiro(store):
    with pytest.raises(TransferNotAuthorizedError):
        make_service(store, FakeAuthorizer("denied")).execute(
            value=Decimal("40.00"), payer_id=1, payee_id=2
        )

    assert store.wallets[1].balance == Decimal("100.00")
    assert store.wallets[2].balance == Decimal("50.00")
    assert len(store.transfers) == 0


def test_autorizador_indisponivel_nao_move_dinheiro(store):
    # na duvida ("nao sei a resposta"), dinheiro nao se move
    with pytest.raises(AuthorizerUnavailableError):
        make_service(store, FakeAuthorizer("unavailable")).execute(
            value=Decimal("40.00"), payer_id=1, payee_id=2
        )

    assert store.wallets[1].balance == Decimal("100.00")
    assert len(store.transfers) == 0


def test_revalidacao_pos_lock_cobre_a_janela_do_autorizador(store):
    # simula outra transferencia drenando o saldo DURANTE a chamada de rede:
    # a pre-checagem passou, mas a revalidacao pos-lock precisa recusar
    def drain_balance():
        store.wallets[1].balance = Decimal("5.00")

    with pytest.raises(InsufficientBalanceError):
        make_service(store, FakeAuthorizer("ok", on_call=drain_balance)).execute(
            value=Decimal("40.00"), payer_id=1, payee_id=2
        )

    assert store.wallets[1].balance == Decimal("5.00")  # intocado pela nossa tentativa
    assert store.wallets[2].balance == Decimal("50.00")
    assert len(store.transfers) == 0


def test_falha_na_notificacao_nao_reverte_a_transferencia(store):
    result = make_service(store, notifier=FakeNotifier(sent=False)).execute(
        value=Decimal("40.00"), payer_id=1, payee_id=2
    )

    # o dinheiro moveu e permanece movido; so o status da notificacao registra a falha
    assert store.wallets[1].balance == Decimal("60.00")
    assert store.wallets[2].balance == Decimal("90.00")
    assert result.status == "completed"
    assert result.notification_status == "failed"
    transfer = next(iter(store.transfers.values()))
    assert transfer.notification_status == "failed"
