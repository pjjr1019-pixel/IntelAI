"""Add trading schema tables

Revision ID: cc502b28cbf2
Revises: 88946614ae12
Create Date: 2026-02-09 20:50:47.224486

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc502b28cbf2'
down_revision: Union[str, None] = '88946614ae12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create portfolio table
    op.create_table('portfolio',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.String(length=256), nullable=True),
        sa.Column('updated_by', sa.String(length=256), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('currency', sa.String(length=3), server_default='USD', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_paper_trading', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('cash_balance', sa.Numeric(precision=20, scale=8), server_default='0.00', nullable=False),
        sa.Column('total_value', sa.Numeric(precision=20, scale=8), server_default='0.00', nullable=False),
        sa.Column('max_position_size', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('max_daily_loss', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('max_drawdown', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('allow_margin', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('allow_short_selling', sa.Boolean(), server_default='false', nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create order table
    op.create_table('order',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.String(length=256), nullable=True),
        sa.Column('updated_by', sa.String(length=256), nullable=True),
        sa.Column('portfolio_id', sa.UUID(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('side', sa.String(length=4), nullable=False),
        sa.Column('order_type', sa.String(length=10), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('price', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('stop_price', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('filled_quantity', sa.Numeric(precision=20, scale=8), server_default='0.00', nullable=False),
        sa.Column('average_fill_price', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('filled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('external_order_id', sa.String(length=256), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolio.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create position table
    op.create_table('position',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.String(length=256), nullable=True),
        sa.Column('updated_by', sa.String(length=256), nullable=True),
        sa.Column('portfolio_id', sa.UUID(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('average_cost', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('current_price', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('market_value', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('unrealized_pnl', sa.Numeric(precision=20, scale=8), server_default='0.00', nullable=False),
        sa.Column('realized_pnl', sa.Numeric(precision=20, scale=8), server_default='0.00', nullable=False),
        sa.Column('opened_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolio.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create risk_metrics table
    op.create_table('risk_metrics',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.String(length=256), nullable=True),
        sa.Column('updated_by', sa.String(length=256), nullable=True),
        sa.Column('portfolio_id', sa.UUID(), nullable=False),
        sa.Column('calculated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('sortino_ratio', sa.Float(), nullable=True),
        sa.Column('max_drawdown', sa.Float(), nullable=True),
        sa.Column('value_at_risk', sa.Float(), nullable=True),
        sa.Column('expected_shortfall', sa.Float(), nullable=True),
        sa.Column('volatility', sa.Float(), nullable=True),
        sa.Column('beta', sa.Float(), nullable=True),
        sa.Column('largest_position_pct', sa.Float(), nullable=True),
        sa.Column('top_10_positions_pct', sa.Float(), nullable=True),
        sa.Column('daily_turnover', sa.Float(), nullable=True),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('profit_factor', sa.Float(), nullable=True),
        sa.Column('risk_warnings', sa.JSON(), server_default='{}', nullable=False),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolio.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_portfolio_user_id', 'portfolio', ['user_id'], unique=True)
    op.create_index('ix_portfolio_is_active', 'portfolio', ['is_active'], unique=False)
    op.create_index('ix_order_portfolio_id', 'order', ['portfolio_id'], unique=False)
    op.create_index('ix_order_symbol', 'order', ['symbol'], unique=False)
    op.create_index('ix_order_status', 'order', ['status'], unique=False)
    op.create_index('ix_order_created_at', 'order', ['created_at'], unique=False)
    op.create_index('ix_position_portfolio_symbol', 'position', ['portfolio_id', 'symbol'], unique=True)
    op.create_index('ix_position_portfolio_id', 'position', ['portfolio_id'], unique=False)
    op.create_index('ix_position_symbol', 'position', ['symbol'], unique=False)
    op.create_index('ix_risk_metrics_portfolio_date', 'risk_metrics', ['portfolio_id', 'calculated_at'], unique=False)
    op.create_index('ix_risk_metrics_portfolio_id', 'risk_metrics', ['portfolio_id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_risk_metrics_portfolio_id', table_name='risk_metrics')
    op.drop_index('ix_risk_metrics_portfolio_date', table_name='risk_metrics')
    op.drop_index('ix_position_symbol', table_name='position')
    op.drop_index('ix_position_portfolio_id', table_name='position')
    op.drop_index('ix_position_portfolio_symbol', table_name='position')
    op.drop_index('ix_order_created_at', table_name='order')
    op.drop_index('ix_order_status', table_name='order')
    op.drop_index('ix_order_symbol', table_name='order')
    op.drop_index('ix_order_portfolio_id', table_name='order')
    op.drop_index('ix_portfolio_is_active', table_name='portfolio')
    op.drop_index('ix_portfolio_user_id', table_name='portfolio')

    # Drop tables
    op.drop_table('risk_metrics')
    op.drop_table('position')
    op.drop_table('order')
    op.drop_table('portfolio')
