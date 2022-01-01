"""Add custom commands

Revision ID: 19a1e9824831
Revises: 2b3b52dd4733
Create Date: 2021-12-31 15:13:31.649480

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "19a1e9824831"
down_revision = "2b3b52dd4733"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "custom_command",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("output", sa.String(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_custom_command_name"),
        "custom_command",
        ["name"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_custom_command_name"), table_name="custom_command")
    op.drop_table("custom_command")
    # ### end Alembic commands ###