"""Add preferred_model to users table

Revision ID: 002
Revises: 001
Create Date: 2026-02-02

This migration adds a preferred_model column to the users table
so each user can persist their default AI model selection.

Safe for deployed databases:
- add_column with nullable=True + server_default is non-locking on PostgreSQL
- downgrade cleanly drops the column
- Existing rows receive 'gpt-4o' as default
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'preferred_model',
            sa.String(50),
            nullable=True,
            server_default='gpt-4o',
        ),
    )


def downgrade() -> None:
    op.drop_column('users', 'preferred_model')
