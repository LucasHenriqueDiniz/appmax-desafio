from decimal import Decimal

from app.domain.enums import UserType
from app.infrastructure.database.models import UserModel, WalletModel


def seed_user(
    session_factory,
    user_id: int,
    balance: str,
    user_type: UserType = UserType.COMMON,
) -> None:
    with session_factory() as session, session.begin():
        session.add(
            UserModel(
                id=user_id,
                full_name=f"Usuario {user_id}",
                document=f"doc-{user_id}",
                email=f"user{user_id}@test.com",
                password_hash="hash",
                type=user_type,
            )
        )
        session.add(WalletModel(user_id=user_id, balance=Decimal(balance)))


def get_balance(session_factory, user_id: int) -> Decimal:
    with session_factory() as session:
        return session.get(WalletModel, user_id).balance
