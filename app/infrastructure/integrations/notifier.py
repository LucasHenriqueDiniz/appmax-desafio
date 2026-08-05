import logging

import httpx

logger = logging.getLogger("app.notifier")


class NotifierClient:
    """Cliente do notificador externo (util.devi.tools).

    Comportamento real verificado (2026-08-05): 204 em sucesso; 504 em
    ~1/3 das chamadas (falha aleatoria proposital do servico).

    Roda DEPOIS do commit, entao nunca segura lock. 1 retry eleva o
    sucesso de ~67% para ~89%. Falha definitiva retorna False — quem
    decide o que fazer (marcar failed e logar) e o use case; a
    transferencia ja concluida jamais e revertida por causa disso.
    """

    MAX_ATTEMPTS = 2

    def __init__(self, url: str, timeout: float):
        self._url = url
        self._client = httpx.Client(timeout=timeout)

    def notify(self) -> bool:
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
                response = self._client.post(self._url)
            except httpx.RequestError as exc:
                logger.warning("notificador inalcancavel (tentativa %d): %s", attempt, exc)
                continue
            if response.status_code in (200, 204):
                return True
            logger.warning(
                "notificador respondeu %s (tentativa %d)", response.status_code, attempt
            )
        return False

    def close(self) -> None:
        self._client.close()
