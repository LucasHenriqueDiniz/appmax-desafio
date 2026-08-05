"""Logs coloridos, alinhados e com key=value destacado — sem dependencia externa.

Um unico formato para a aplicacao E para o uvicorn (por padrao cada um
loga de um jeito). Respeita NO_COLOR (https://no-color.org) para
ambientes que nao renderizam ANSI.
"""

import logging
import os
import re

from app.request_context import request_id_var

_RESET = "\x1b[0m"
_DIM = "\x1b[2m"
_BOLD = "\x1b[1m"
_LEVEL_COLORS = {
    logging.DEBUG: "\x1b[36m",
    logging.INFO: "\x1b[32m",
    logging.WARNING: "\x1b[33m",
    logging.ERROR: "\x1b[31m",
    logging.CRITICAL: "\x1b[1;41m",
}
_KEY_VALUE = re.compile(r"\b(\w+)=(\S+)")


class ColorFormatter(logging.Formatter):
    def __init__(self, use_colors: bool):
        super().__init__()
        self._use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%H:%M:%S")
        name = record.name.removeprefix("app.")
        message = record.getMessage()
        # correlaciona linhas da mesma requisicao sob concorrencia;
        # fora de requisicao (boot, seed) o campo fica vazio
        request_id = request_id_var.get()
        rid = f"[{request_id}] " if request_id != "-" else ""

        if self._use_colors:
            level_color = _LEVEL_COLORS.get(record.levelno, "")
            message = _KEY_VALUE.sub(rf"{_DIM}\1={_RESET}{_BOLD}\2{_RESET}", message)
            line = (
                f"{_DIM}{timestamp}{_RESET} "
                f"{level_color}{record.levelname:<8}{_RESET} "
                f"{_DIM}{name:<15}{_RESET} {_DIM}{rid}{_RESET}{message}"
            )
        else:
            line = f"{timestamp} {record.levelname:<8} {name:<15} {rid}{message}"

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter(use_colors="NO_COLOR" not in os.environ))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)

    # os loggers do uvicorn passam a propagar para o root: um estilo so
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
