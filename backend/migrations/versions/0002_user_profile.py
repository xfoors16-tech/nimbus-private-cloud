"""Add editable user profile fields and private avatars."""

from alembic import op
import sqlalchemy as sa

revision = "0002_user_profile"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(length=32), server_default="", nullable=False))
    op.add_column("users", sa.Column("avatar_key", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("avatar_mime_type", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_mime_type")
    op.drop_column("users", "avatar_key")
    op.drop_column("users", "phone")
