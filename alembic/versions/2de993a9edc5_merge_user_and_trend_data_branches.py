"""Merge user and trend data branches

Revision ID: 2de993a9edc5
Revises: 0002_add_users, 0003_trend_data
Create Date: 2026-02-08 22:54:51.061655

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2de993a9edc5'
down_revision: Union[str, None] = ('0002_add_users', '0003_trend_data')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
