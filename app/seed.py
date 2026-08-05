"""Seed idempotente: cria usuarios de exemplo apenas se ainda nao existirem.

IDs explicitos de proposito: o payload de exemplo do enunciado
({"value": 100.0, "payer": 4, "payee": 15}) funciona copiado e colado.
Rodar de novo NAO duplica usuarios nem reseta saldos ja movimentados.
"""

import hashlib
import logging
import os
from decimal import Decimal

from sqlalchemy import select, text

from app.domain.enums import UserType
from app.infrastructure.database.models import UserModel, WalletModel
from app.infrastructure.database.session import SessionFactory

logger = logging.getLogger("app.seed")

# (id, nome, CPF/CNPJ, email, tipo, saldo inicial)
SEED_USERS = [
    (1, "Ana Souza", "52998224725", "ana@example.com", UserType.COMMON, Decimal("1000.00")),
    (2, "Bruno Lima", "15350946056", "bruno@example.com", UserType.COMMON, Decimal("100.00")),
    (3, "Carla Dias", "11144477735", "carla@example.com", UserType.COMMON, Decimal("0.00")),
    (4, "Daniel Alves", "86288366757", "daniel@example.com", UserType.COMMON, Decimal("500.00")),
    (
        5,
        "Mercado da Maria",
        "11222333000181",
        "mercado.maria@example.com",
        UserType.MERCHANT,
        Decimal("250.00"),
    ),
    (
        15,
        "Loja do Ze",
        "60746948000112",
        "loja.ze@example.com",
        UserType.MERCHANT,
        Decimal("0.00"),
    ),
]


def _hash_password(plain: str) -> str:
    # Nao ha login no escopo; o hash existe apenas para nunca guardar senha em claro.
    # scrypt da stdlib evita uma dependencia so para isso (em producao: argon2/bcrypt).
    salt = os.urandom(16)
    digest = hashlib.scrypt(plain.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def run() -> None:
    with SessionFactory() as session, session.begin():
        created = 0
        for user_id, name, document, email, user_type, balance in SEED_USERS:
            exists = session.scalar(select(UserModel.id).where(UserModel.document == document))
            if exists is not None:
                continue
            session.add(
                UserModel(
                    id=user_id,
                    full_name=name,
                    document=document,
                    email=email,
                    password_hash=_hash_password("senha-exemplo"),
                    type=user_type,
                )
            )
            session.add(WalletModel(user_id=user_id, balance=balance))
            created += 1

        # INSERTs com id explicito nao avancam a sequence do Postgres;
        # realinha para que futuros INSERTs sem id nao colidam
        session.execute(text("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users))"))

    logger.info("seed concluido: %d usuario(s) criado(s)", created)


if __name__ == "__main__":
    from app.logging_config import setup_logging

    setup_logging()
    run()
