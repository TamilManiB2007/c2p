"""Add compliance columns and table

Revision ID: 004
Revises: 003
Create Date: 2026-06-10 21:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns to contracts table
    op.add_column("contracts", sa.Column("end_date", sa.Date(), nullable=True))
    op.add_column("contracts", sa.Column("contract_amount", sa.Numeric(precision=12, scale=2), nullable=True))

    # Create compliance_checks table
    op.create_table(
        "compliance_checks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("check_type", sa.String(length=50), nullable=False),
        sa.Column(
            "status",
            sa.Enum("passed", "failed", name="compliancestatus"),
            nullable=False,
            server_default="passed",
        ),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_compliance_checks_id"), "compliance_checks", ["id"], unique=False)
    op.create_index(op.f("ix_compliance_checks_contract_id"), "compliance_checks", ["contract_id"], unique=False)
    op.create_index(op.f("ix_compliance_checks_invoice_id"), "compliance_checks", ["invoice_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_compliance_checks_invoice_id"), table_name="compliance_checks")
    op.drop_index(op.f("ix_compliance_checks_contract_id"), table_name="compliance_checks")
    op.drop_index(op.f("ix_compliance_checks_id"), table_name="compliance_checks")
    op.drop_table("compliance_checks")
    op.execute("DROP TYPE compliancestatus")

    op.drop_column("contracts", "contract_amount")
    op.drop_column("contracts", "end_date")
