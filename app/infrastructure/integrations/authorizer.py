import logging

import httpx

from app.domain.exceptions import AuthorizerUnavailableError, TransferNotAuthorizedError

logger = logging.getLogger("app.authorizer")


class AuthorizerClient:
    """Cliente do autorizador externo (util.devi.tools).

    Comportamento real verificado (2026-08-05):
      - autoriza: 200 + {"status": "success", "data": {"authorization": true}}
      - nega:     403 + {"status": "fail", "data": {"authorization": false}}

    Tres resultados distintos:
      - autorizado   -> retorna silenciosamente
      - negado       -> TransferNotAuthorizedError (403 e RESPOSTA de negocio, nao erro)
      - indisponivel -> AuthorizerUnavailableError (timeout, 5xx, corpo invalido:
                        nao sabemos a resposta e, na duvida, dinheiro nao se move)

    Sem retry: negacao e uma resposta definitiva, nao uma falha.
    """

    def __init__(self, url: str, timeout: float):
        self._url = url
        self._client = httpx.Client(timeout=timeout)

    def authorize(self) -> None:
        try:
            response = self._client.get(self._url)
        except httpx.RequestError as exc:
            logger.warning("autorizador inalcancavel: %s", exc)
            raise AuthorizerUnavailableError() from exc

        # 200 (autorizado) e 403 (negado) sao os dois status conhecidos;
        # qualquer outro e comportamento inesperado => indisponivel
        if response.status_code not in (200, 403):
            logger.warning("autorizador respondeu status inesperado: %s", response.status_code)
            raise AuthorizerUnavailableError()

        try:
            authorized = bool(response.json()["data"]["authorization"])
        except (ValueError, KeyError, TypeError) as exc:
            logger.warning("autorizador respondeu corpo invalido")
            raise AuthorizerUnavailableError() from exc

        # o corpo e a fonte de verdade
        if not authorized:
            raise TransferNotAuthorizedError()

    def close(self) -> None:
        self._client.close()
