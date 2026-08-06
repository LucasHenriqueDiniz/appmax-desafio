"""Reseta o banco ao estado do seed: saldos originais e historico limpo.

Feito para demonstracoes — entre um take e outro:

    uv run python scripts/reset_demo.py
"""

from decimal import Decimal

from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg://appmax:appmax@localhost:5432/appmax"

SEED_BALANCES = {1: "1000.00", 2: "100.00", 3: "0.00", 4: "500.00", 5: "250.00", 15: "0.00"}


def main() -> None:
    engine = create_engine(DB_URL, connect_args={"connect_timeout": 3})
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE transfers"))
        for user_id, balance in SEED_BALANCES.items():
            connection.execute(
                text("UPDATE wallets SET balance = :balance WHERE user_id = :user_id"),
                {"balance": Decimal(balance), "user_id": user_id},
            )
    print("banco resetado: saldos do seed restaurados, historico de transferencias limpo")


if __name__ == "__main__":
    main()
