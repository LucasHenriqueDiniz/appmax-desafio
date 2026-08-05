"""Fiacao completa (rota -> use case -> Postgres) com o payload EXATO do enunciado."""

import logging
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.application.transfer_service import TransferService
from app.domain.enums import UserType
from app.infrastructure.database.repositories import SqlAlchemyUnitOfWork
from app.main import app
from tests.integration.helpers import get_balance, seed_user
from tests.unit.fakes import FakeAuthorizer, FakeNotifier

pytestmark = pytest.mark.integration


@pytest.fixture
def client(session_factory):
    with TestClient(app) as test_client:
        # troca o service montado no lifespan por um que usa o banco de teste
        # e dubles das integracoes (a rede real e testada em test_authorizer_client)
        app.state.transfer_service = TransferService(
            uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
            authorizer=FakeAuthorizer(),
            notifier=FakeNotifier(),
        )
        yield test_client


def test_contrato_do_enunciado_funciona_como_esta_escrito(client, session_factory):
    seed_user(session_factory, 4, "500.00")
    seed_user(session_factory, 15, "0.00", UserType.MERCHANT)

    response = client.post("/transfer", json={"value": 100.0, "payer": 4, "payee": 15})

    assert response.status_code == 201
    assert response.headers["x-request-id"]  # correlaciona logs de uma mesma requisicao
    body = response.json()
    assert body["status"] == "completed"
    assert body["payer"] == 4
    assert body["payee"] == 15
    assert Decimal(body["value"]) == Decimal("100.00")
    assert get_balance(session_factory, 4) == Decimal("400.00")
    assert get_balance(session_factory, 15) == Decimal("100.00")


def test_lojista_pagador_responde_422_com_codigo(client, session_factory, caplog):
    seed_user(session_factory, 4, "500.00")
    seed_user(session_factory, 15, "0.00", UserType.MERCHANT)

    with caplog.at_level(logging.INFO, logger="app.api"):
        response = client.post("/transfer", json={"value": 10.0, "payer": 15, "payee": 4})

    assert response.status_code == 422
    assert response.json()["code"] == "MERCHANT_CANNOT_TRANSFER"
    # recusas de negocio deixam rastro nos logs (observabilidade)
    assert any("MERCHANT_CANNOT_TRANSFER" in record.getMessage() for record in caplog.records)


def test_saldo_insuficiente_responde_409(client, session_factory):
    seed_user(session_factory, 4, "5.00")
    seed_user(session_factory, 15, "0.00", UserType.MERCHANT)

    response = client.post("/transfer", json={"value": 10.0, "payer": 4, "payee": 15})

    assert response.status_code == 409
    assert response.json()["code"] == "INSUFFICIENT_BALANCE"


def test_id_fora_do_range_do_banco_responde_422_nao_500(client, session_factory):
    # achado de revisao de seguranca: int maior que o INTEGER do Postgres
    # deve morrer na validacao da borda, nao estourar no driver
    response = client.post(
        "/transfer", json={"value": 10.0, "payer": 99999999999999999999, "payee": 2}
    )

    assert response.status_code == 422


def test_pagador_inexistente_responde_404(client, session_factory):
    seed_user(session_factory, 4, "500.00")

    response = client.post("/transfer", json={"value": 10.0, "payer": 999, "payee": 4})

    assert response.status_code == 404
    assert response.json()["code"] == "USER_NOT_FOUND"
