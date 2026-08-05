import httpx
import pytest
import respx

from app.infrastructure.integrations.notifier import NotifierClient

URL = "https://notifier.test/api/v1/notify"


@pytest.fixture
def client():
    instance = NotifierClient(URL, timeout=1.0)
    yield instance
    instance.close()


@respx.mock
def test_204_significa_entregue(client):
    route = respx.post(URL).respond(204)

    assert client.notify() is True
    assert route.call_count == 1


@respx.mock
def test_falha_transitoria_resolvida_pelo_retry(client):
    # comportamento real do endpoint: 504 aleatorio em ~1/3 das chamadas
    route = respx.post(URL)
    route.side_effect = [httpx.Response(504), httpx.Response(204)]

    assert client.notify() is True
    assert route.call_count == 2


@respx.mock
def test_falha_definitiva_retorna_false_sem_excecao(client):
    route = respx.post(URL).respond(504)

    assert client.notify() is False
    assert route.call_count == 2  # tentou, re-tentou, desistiu


@respx.mock
def test_connection_error_tambem_conta_como_tentativa(client):
    route = respx.post(URL)
    route.side_effect = [httpx.ConnectError("down"), httpx.Response(204)]

    assert client.notify() is True
    assert route.call_count == 2
