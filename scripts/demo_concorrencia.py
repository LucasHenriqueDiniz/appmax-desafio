"""Corrida ao vivo: duas transferencias simultaneas saindo da mesma conta.

Usa o MESMO caminho de codigo da API (TransferService + SELECT FOR UPDATE),
disparado em duas threads soltas no mesmo instante, no banco da aplicacao —
o painel (watch_saldos) mostra o resultado em tempo real.

Uso:
    docker compose up -d
    uv run python scripts/demo_concorrencia.py
"""

import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

# roda como script solto (python scripts/...), entao o pacote `app` precisa
# entrar no path manualmente
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text

from app.application.transfer_service import TransferService
from app.domain.exceptions import InsufficientBalanceError
from app.infrastructure.database.repositories import SqlAlchemyUnitOfWork

DB_URL = "postgresql+psycopg://appmax:appmax@localhost:5432/appmax"

RESET = "\x1b[0m"
DIM = "\x1b[2m"
BOLD = "\x1b[1m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
CYAN = "\x1b[36m"

PAYER, PAYEE_A, PAYEE_B = 2, 1, 3
VALOR = Decimal("80.00")


class _SempreAutoriza:
    """Duble do autorizador: aqui o assunto e o lock, nao a rede.

    (A API de verdade continua consultando o autorizador externo.)
    """

    def authorize(self) -> None:
        pass


class _NotificaOk:
    def notify(self) -> bool:
        return True


def get_balance(connection, user_id: int) -> Decimal:
    return connection.execute(
        text("SELECT balance FROM wallets WHERE user_id = :id"), {"id": user_id}
    ).scalar_one()


def get_total(connection) -> Decimal:
    return connection.execute(text("SELECT SUM(balance) FROM wallets")).scalar_one()


def main() -> None:
    os.system("")  # habilita ANSI no console classico do Windows
    engine = create_engine(DB_URL, connect_args={"connect_timeout": 3})

    with engine.begin() as connection:
        connection.execute(
            text("UPDATE wallets SET balance = 100 WHERE user_id = :id"), {"id": PAYER}
        )
    with engine.connect() as connection:
        soma_antes = get_total(connection)

    print()
    print(f"{BOLD}  CORRIDA: duas transferencias de R$ {VALOR} saindo da MESMA conta{RESET}")
    print(f"    pagador #{PAYER} comeca com {BOLD}R$ 100.00{RESET}")
    print(f"    {CYAN}thread A{RESET}: #{PAYER} -> #{PAYEE_A}  R$ {VALOR}")
    print(f"    {CYAN}thread B{RESET}: #{PAYER} -> #{PAYEE_B}  R$ {VALOR}")
    print(f"    {DIM}as duas soltas no mesmo instante, no mesmo codigo da API{RESET}")
    print()

    service = TransferService(
        uow_factory=SqlAlchemyUnitOfWork,
        authorizer=_SempreAutoriza(),
        notifier=_NotificaOk(),
    )
    barrier = threading.Barrier(2)

    def attempt(payee_id: int) -> str:
        barrier.wait()  # segura as duas threads e solta juntas
        try:
            service.execute(value=VALOR, payer_id=PAYER, payee_id=payee_id)
            return "concluida"
        except InsufficientBalanceError:
            return "recusada"

    with ThreadPoolExecutor(max_workers=2) as pool:
        future_a = pool.submit(attempt, PAYEE_A)
        future_b = pool.submit(attempt, PAYEE_B)
        results = {"A": future_a.result(timeout=30), "B": future_b.result(timeout=30)}

    for name, outcome in results.items():
        if outcome == "concluida":
            print(f"    thread {name}: {GREEN}{BOLD}CONCLUIDA{RESET}")
        else:
            motivo = f"{DIM}(saldo insuficiente){RESET}"
            print(f"    thread {name}: {YELLOW}{BOLD}RECUSADA{RESET} {motivo}")

    with engine.connect() as connection:
        saldo_final = get_balance(connection, PAYER)
        soma_depois = get_total(connection)

    print()
    print(f"    saldo final do pagador #{PAYER}: {BOLD}R$ {saldo_final}{RESET}")
    igual = f"{GREEN}{BOLD}igual{RESET}" if soma_antes == soma_depois else "DIFERENTE?!"
    print(f"    soma de todos os saldos: R$ {soma_antes} antes, R$ {soma_depois} depois — {igual}")
    print(f"    {DIM}exatamente uma passou; dinheiro nao nasceu nem sumiu{RESET}")
    print()


if __name__ == "__main__":
    main()
