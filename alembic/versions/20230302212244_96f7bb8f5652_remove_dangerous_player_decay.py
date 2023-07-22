"""Remove dangerous player decay

Revision ID: 96f7bb8f5652
Revises: e14c46b66983
Create Date: 2023-03-02 21:22:44.978087

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "96f7bb8f5652"
down_revision = "e14c46b66983"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("player_decay", schema=None) as batch_op:
        batch_op.drop_index("ix_player_decay_player_id")

    op.drop_table("player_decay")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "player_decay",
        sa.Column(
            "player_id", sa.BIGINT(), autoincrement=False, nullable=False
        ),
        sa.Column(
            "decay_percentage",
            postgresql.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "decayed_at",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("id", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column(
            "rated_trueskill_mu_before",
            postgresql.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "rated_trueskill_mu_after",
            postgresql.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "unrated_trueskill_mu_before",
            postgresql.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "unrated_trueskill_mu_after",
            postgresql.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["player.id"],
            name="fk_player_decay_player_id_player",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_player_decay"),
    )
    with op.batch_alter_table("player_decay", schema=None) as batch_op:
        batch_op.create_index(
            "ix_player_decay_player_id", ["player_id"], unique=False
        )

    # ### end Alembic commands ###