"""Demonstracao guiada da API: roda os cenarios principais e mostra os saldos mudando.

Uso:
    docker compose up -d            # API e banco de pe
    uv run python scripts/demo.py
"""

import sys

import httpx
from sqlalchemy import create_engine, text

API = "http://localhost:8000"
DB_URL = "postgresql+psycopg://appmax:appmax@localhost:5432/appmax"

engine = create_engine(DB_URL)


def get_balances() -> list[tuple]:
    query = """
        SELECT u.id, u.full_name, u.type, w.balance
        FROM users u JOIN wallets w ON w.user_id = u.id
        ORDER BY u.id
    """
    with engine.connect() as connection:
        return connection.execute(text(query)).all()


def show_balances(title: str) -> None:
    rows = get_balances()
    total = sum(balance for _, _, _, balance in rows)
    print(f"\n  {title}")
    for user_id, name, user_type, balance in rows:
        tag = "[lojista]" if user_type == "merchant" else "[comum]  "
        print(f"    {tag} #{user_id:<3} {name:<20} R$ {balance:>10}")
    print(f"    {'soma de todos os saldos':>34}: R$ {total:>10}   <- invariante!")


def post_transfer(value: float, payer: int, payee: int) -> httpx.Response:
    return httpx.post(
        f"{API}/transfer",
        json={"value": value, "payer": payer, "payee": payee},
        timeout=30,
    )


def scenario(title: str, explanation: str, value: float, payer: int, payee: int) -> None:
    print(f"\n{'=' * 72}")
    print(f"  {title}")
    print(f"  {explanation}")
    print(f"\n  POST /transfer  {{\"value\": {value}, \"payer\": {payer}, \"payee\": {payee}}}")

    # o autorizador REAL nega aleatoriamente (~1/3): parte do desafio.
    # aqui re-tentamos so para a demo nao parar; a API em si NAO faz retry.
    for attempt in range(1, 6):
        response = post_transfer(value, payer, payee)
        body = response.json()
        if response.status_code == 403 and body.get("code") == "TRANSFER_NOT_AUTHORIZED":
            print(f"  -> HTTP 403 {body['code']} (autorizador externo negou aleatoriamente)")
            print(f"     ... tentando de novo ({attempt}/5) — nada mudou no banco")
            continue
        break

    print(f"  -> HTTP {response.status_code}")
    for key, val in body.items():
        print(f"       {key}: {val}")


def main() -> None:
    try:
        health = httpx.get(f"{API}/health", timeout=5).json()
    except httpx.RequestError:
        print("ERRO: API fora do ar. Rode antes:  docker compose up -d")
        sys.exit(1)
    print(f"API de pe: {health}")

    show_balances("Saldos iniciais (criados pelo seed):")

    scenario(
        "CENARIO 1 — o contrato exato do enunciado",
        "Usuario 4 (comum, com saldo) transfere 100 para o 15 (lojista). Esperado: 201.",
        100.0,
        4,
        15,
    )
    show_balances("Saldos depois (repare: 4 perdeu 100, 15 ganhou 100, soma igual):")

    scenario(
        "CENARIO 2 — lojista tentando pagar",
        "Lojista so recebe, nunca paga. Esperado: 422 MERCHANT_CANNOT_TRANSFER.",
        10.0,
        15,
        4,
    )

    scenario(
        "CENARIO 3 — saldo insuficiente",
        "Ninguem tem 99999. Esperado: 409 INSUFFICIENT_BALANCE.",
        99999.0,
        1,
        2,
    )

    scenario(
        "CENARIO 4 — usuario que nao existe",
        "Payer 777 nao esta no banco. Esperado: 404 USER_NOT_FOUND.",
        10.0,
        777,
        2,
    )

    scenario(
        "CENARIO 5 — transferir para si mesmo",
        "payer == payee nao faz sentido. Esperado: 422 INVALID_TRANSFER.",
        10.0,
        1,
        1,
    )

    show_balances("Saldos finais (cenarios 2-5 nao mudaram NADA — so o cenario 1 moveu dinheiro):")

    print(f"\n{'=' * 72}")
    print("  Fim. Para ver os logs do servidor (cada recusa deixa rastro):")
    print("    docker compose logs api | findstr recusada")
    print("  Para o teste de concorrencia (o mais importante do projeto):")
    print("    uv run pytest tests/integration/test_concurrency.py -v")


if __name__ == "__main__":
    main()
