"""Add contact fields to users table.

Revision ID: 002
Revises: 001_add_subscriptions
Create Date: 2024-12-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_add_user_contact_fields'
down_revision: Union[str, None] = '001_add_subscriptions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add contact info fields to users table
    op.add_column('users', sa.Column('full_name', sa.String(255), nullable=True), schema='jobseeker')
    op.add_column('users', sa.Column('phone', sa.String(50), nullable=True), schema='jobseeker')
    op.add_column('users', sa.Column('profile_picture_url', sa.String(500), nullable=True), schema='jobseeker')


def downgrade() -> None:
    op.drop_column('users', 'profile_picture_url', schema='jobseeker')
    op.drop_column('users', 'phone', schema='jobseeker')
    op.drop_column('users', 'full_name', schema='jobseeker')
