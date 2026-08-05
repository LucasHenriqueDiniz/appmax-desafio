"""cria users, wallets e transfers

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("document", sa.String(18), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.UniqueConstraint("document", name="uq_users_document"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("type IN ('common', 'merchant')", name="ck_users_type"),
    )

    op.create_table(
        "wallets",
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True
        ),
        sa.Column("balance", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        # o banco como ultima linha de defesa: saldo negativo e impossivel
        sa.CheckConstraint("balance >= 0", name="ck_wallets_balance_non_negative"),
    )

    op.create_table(
        "transfers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("payer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("payee_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("notification_status", sa.String(20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint("amount > 0", name="ck_transfers_amount_positive"),
        sa.CheckConstraint("payer_id <> payee_id", name="ck_transfers_distinct_users"),
    )
    op.create_index("ix_transfers_payer_id", "transfers", ["payer_id"])
    op.create_index("ix_transfers_payee_id", "transfers", ["payee_id"])


def downgrade() -> None:
    op.drop_table("transfers")
    op.drop_table("wallets")
    op.drop_table("users")
