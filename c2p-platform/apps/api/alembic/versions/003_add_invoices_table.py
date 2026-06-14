"""Add invoices table

Revision ID: 003
Revises: 002
Create Date: 2026-06-10 20:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_number", sa.String(length=100), nullable=False),
        sa.Column("vendor_name", sa.String(length=255), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column(
            "status",
            sa.Enum("uploaded", "processing", "processed", "failed", name="invoicestatus"),
            nullable=False,
            server_default="uploaded",
        ),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_number"),
    )
    op.create_index(op.f("ix_invoices_id"), "invoices", ["id"], unique=False)
    op.create_index(op.f("ix_invoices_invoice_number"), "invoices", ["invoice_number"], unique=True)
    op.create_index(op.f("ix_invoices_vendor_name"), "invoices", ["vendor_name"], unique=False)
    op.create_index(op.f("ix_invoices_uploaded_by"), "invoices", ["uploaded_by"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_invoices_uploaded_by"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_vendor_name"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_invoice_number"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_id"), table_name="invoices")
    op.drop_table("invoices")
    op.execute("DROP TYPE invoicestatus")
