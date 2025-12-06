"""Add subscription and usage_logs tables.

Revision ID: 001
Revises:
Create Date: 2024-12-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_add_subscriptions'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE jobseeker.subscription_tier AS ENUM ('free', 'starter', 'pro', 'power');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE jobseeker.usage_action_type AS ENUM (
                'proposal_generate',
                'proposal_enhance',
                'jd_parse',
                'resume_parse',
                'job_search'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tier', postgresql.ENUM('free', 'starter', 'pro', 'power', name='subscription_tier', schema='jobseeker', create_type=False), nullable=False, server_default='free'),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),
        sa.Column('stripe_price_id', sa.String(255), nullable=True),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('canceled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('proposal_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('jd_parse_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('job_search_count_today', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('usage_reset_date', sa.Date(), nullable=True),
        sa.Column('daily_reset_date', sa.Date(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['jobseeker.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_subscription_id'),
        sa.UniqueConstraint('user_id'),
        schema='jobseeker'
    )

    op.create_index('ix_jobseeker_subscriptions_user_id', 'subscriptions', ['user_id'], schema='jobseeker')
    op.create_index('ix_jobseeker_subscriptions_stripe_customer_id', 'subscriptions', ['stripe_customer_id'], schema='jobseeker')

    # Create usage_logs table
    op.create_table(
        'usage_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action_type', postgresql.ENUM('proposal_generate', 'proposal_enhance', 'jd_parse', 'resume_parse', 'job_search', name='usage_action_type', schema='jobseeker', create_type=False), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('cost_cents', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['subscription_id'], ['jobseeker.subscriptions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='jobseeker'
    )

    op.create_index('ix_jobseeker_usage_logs_subscription_id', 'usage_logs', ['subscription_id'], schema='jobseeker')
    op.create_index('ix_jobseeker_usage_logs_created_at', 'usage_logs', ['created_at'], schema='jobseeker')


def downgrade() -> None:
    op.drop_table('usage_logs', schema='jobseeker')
    op.drop_table('subscriptions', schema='jobseeker')

    op.execute("DROP TYPE IF EXISTS jobseeker.usage_action_type;")
    op.execute("DROP TYPE IF EXISTS jobseeker.subscription_tier;")
