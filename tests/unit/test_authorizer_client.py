"""Cenarios reproduzidos do comportamento REAL do endpoint (verificado em 2026-08-05)."""

import httpx
import pytest
import respx

from app.domain.exceptions import AuthorizerUnavailableError, TransferNotAuthorizedError
from app.infrastructure.integrations.authorizer import AuthorizerClient

URL = "https://authorizer.test/api/v2/authorize"


@pytest.fixture
def client():
    instance = AuthorizerClient(URL, timeout=1.0)
    yield instance
    instance.close()


@respx.mock
def test_autorizado_retorna_silenciosamente(client):
    respx.get(URL).respond(200, json={"status": "success", "data": {"authorization": True}})

    client.authorize()  # nao levanta


@respx.mock
def test_negado_com_403_e_resposta_de_negocio(client):
    respx.get(URL).respond(403, json={"status": "fail", "data": {"authorization": False}})

    with pytest.raises(TransferNotAuthorizedError):
        client.authorize()


@respx.mock
def test_corpo_e_a_fonte_de_verdade_mesmo_com_200(client):
    respx.get(URL).respond(200, json={"status": "success", "data": {"authorization": False}})

    with pytest.raises(TransferNotAuthorizedError):
        client.authorize()


@respx.mock
def test_timeout_significa_indisponivel(client):
    respx.get(URL).mock(side_effect=httpx.ConnectTimeout("timeout"))

    with pytest.raises(AuthorizerUnavailableError):
        client.authorize()


@respx.mock
def test_erro_5xx_significa_indisponivel(client):
    respx.get(URL).respond(500)

    with pytest.raises(AuthorizerUnavailableError):
        client.authorize()


@respx.mock
def test_status_inesperado_significa_indisponivel(client):
    respx.get(URL).respond(302)

    with pytest.raises(AuthorizerUnavailableError):
        client.authorize()


@respx.mock
def test_corpo_invalido_significa_indisponivel(client):
    respx.get(URL).respond(200, content=b"isso nao e json")

    with pytest.raises(AuthorizerUnavailableError):
        client.authorize()
