"""Fixtures de integracao: Postgres REAL, nunca SQLite.

O comportamento de SELECT FOR UPDATE no SQLite nao representa o do
Postgres — o teste de concorrencia passaria sem lock nenhum, o que e
pior que nao ter teste.
"""

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.infrastructure.database.models import Base

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://appmax:appmax@localhost:5432/appmax_test",
)


@pytest.fixture(scope="session")
def engine():
    url = make_url(TEST_DATABASE_URL)
    admin_engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as connection:
            exists = connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": url.database},
            )
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    except OperationalError:
        pytest.skip("Postgres indisponivel — suba com: docker compose up -d db")
    finally:
        admin_engine.dispose()

    test_engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session_factory(engine):
    with engine.connect() as connection:
        connection.execute(text("TRUNCATE transfers, wallets, users RESTART IDENTITY CASCADE"))
        connection.commit()
    return sessionmaker(bind=engine, expire_on_commit=False)
