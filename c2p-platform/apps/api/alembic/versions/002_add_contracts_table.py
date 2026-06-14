"""Add contracts table

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 11:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contracts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vendor_name", sa.String(length=255), nullable=False),
        sa.Column("contract_number", sa.String(length=100), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column(
            "upload_date",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "status",
            sa.Enum("uploaded", "processing", "processed", "failed", name="contractstatus"),
            nullable=False,
            server_default="uploaded",
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contract_number"),
    )
    op.create_index(op.f("ix_contracts_id"), "contracts", ["id"], unique=False)
    op.create_index(op.f("ix_contracts_contract_number"), "contracts", ["contract_number"], unique=True)
    op.create_index(op.f("ix_contracts_vendor_name"), "contracts", ["vendor_name"], unique=False)
    op.create_index(op.f("ix_contracts_created_by"), "contracts", ["created_by"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_contracts_created_by"), table_name="contracts")
    op.drop_index(op.f("ix_contracts_vendor_name"), table_name="contracts")
    op.drop_index(op.f("ix_contracts_contract_number"), table_name="contracts")
    op.drop_index(op.f("ix_contracts_id"), table_name="contracts")
    op.drop_table("contracts")
    op.execute("DROP TYPE contractstatus")